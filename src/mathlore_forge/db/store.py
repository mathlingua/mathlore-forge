"""Store implementation for Mathlore Forge metadata."""

import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from mathlore_forge.db.schema import (
    Base,
    FeedbackModel,
    FeedbackRecord,
    GapModel,
    GapRecord,
    GoldenModel,
    GoldenRecord,
    PhaseType,
    SectionModel,
    SectionRecord,
    TodoItemModel,
    TodoItemRecord,
    TodoStatus,
)
from mathlore_forge.mlg.client import CollectionStructure


class MathloreStore:
    """Manages SQLite/Postgres database persistence for sections, tasks, and feedback."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they don't exist and ensure schema migrations."""
        Base.metadata.create_all(bind=self.engine)
        # Lightweight schema migration for SQLite if defined_commands column is missing
        try:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE sections ADD COLUMN defined_commands TEXT"))
                conn.commit()
        except Exception:
            # Column already exists or table freshly created
            pass

    def sync_from_collection_structure(self, structure: CollectionStructure) -> list[SectionRecord]:
        """Seeds or updates sections from `mlg structure`."""
        records: list[SectionRecord] = []
        with self.SessionLocal() as session:
            # Sync directories
            for idx, d in enumerate(structure.directories):
                existing = session.get(SectionModel, d.path)
                if not existing:
                    new_sec = SectionModel(
                        path=d.path,
                        title=d.title,
                        purpose=f"Chapter/Section directory: {d.title or d.path}",
                        what_covered="",
                        is_directory=True,
                        defined_commands=None,
                        order_index=idx,
                    )
                    session.add(new_sec)
                elif d.title and existing.title != d.title:
                    existing.title = d.title
                    existing.updated_at = datetime.now(timezone.utc)

            # Sync files
            for idx, f in enumerate(structure.files):
                existing = session.get(SectionModel, f.path)
                items_summary = f"{len(f.items)} item(s)"
                commands = f.all_commands
                cmds_json = json.dumps(commands) if commands else None

                if not existing:
                    new_sec = SectionModel(
                        path=f.path,
                        title=f.title,
                        purpose=f"Content page: {f.title or f.path}",
                        what_covered=items_summary,
                        is_directory=False,
                        defined_commands=cmds_json,
                        order_index=len(structure.directories) + idx,
                    )
                    session.add(new_sec)
                else:
                    if f.title and existing.title != f.title:
                        existing.title = f.title
                    existing.what_covered = items_summary
                    existing.defined_commands = cmds_json
                    existing.updated_at = datetime.now(timezone.utc)

            session.commit()

            # Retrieve all updated sections ordered by path
            all_sections = session.execute(
                select(SectionModel).order_by(SectionModel.path)
            ).scalars().all()
            for s in all_sections:
                parsed_cmds = []
                if s.defined_commands:
                    try:
                        parsed_cmds = json.loads(s.defined_commands)
                    except Exception:
                        pass

                records.append(
                    SectionRecord(
                        path=s.path,
                        title=s.title,
                        purpose=s.purpose,
                        what_covered=s.what_covered,
                        prerequisites=s.prerequisites,
                        is_directory=s.is_directory,
                        defined_commands=parsed_cmds,
                        order_index=s.order_index,
                        updated_at=s.updated_at,
                    )
                )
        return records

    def get_sections(self) -> list[SectionRecord]:
        with self.SessionLocal() as session:
            sections = session.execute(
                select(SectionModel).order_by(SectionModel.path)
            ).scalars().all()
            records = []
            for s in sections:
                parsed_cmds = []
                if s.defined_commands:
                    try:
                        parsed_cmds = json.loads(s.defined_commands)
                    except Exception:
                        pass
                records.append(
                    SectionRecord(
                        path=s.path,
                        title=s.title,
                        purpose=s.purpose,
                        what_covered=s.what_covered,
                        prerequisites=s.prerequisites,
                        is_directory=s.is_directory,
                        defined_commands=parsed_cmds,
                        order_index=s.order_index,
                        updated_at=s.updated_at,
                    )
                )
            return records

    def update_section_metadata(
        self, path: str, purpose: str | None = None, what_covered: str | None = None, prerequisites: str | None = None
    ) -> None:
        with self.SessionLocal() as session:
            sec = session.get(SectionModel, path)
            if sec:
                if purpose is not None:
                    sec.purpose = purpose
                if what_covered is not None:
                    sec.what_covered = what_covered
                if prerequisites is not None:
                    sec.prerequisites = prerequisites
                sec.updated_at = datetime.now(timezone.utc)
                session.commit()

    # --- TODO Items Queue ---

    def add_todo_items(self, items: list[TodoItemRecord]) -> None:
        with self.SessionLocal() as session:
            for item in items:
                citations_str = (
                    json.dumps(item.citations)
                    if isinstance(item.citations, (list, dict))
                    else str(item.citations or "")
                )
                model = TodoItemModel(
                    id=item.id,
                    iteration_id=item.iteration_id,
                    section_path=item.section_path,
                    title=item.title,
                    kind=item.kind,
                    purpose=item.purpose,
                    what_to_cover=item.what_to_cover,
                    citations=citations_str,
                    status=item.status.value,
                    source_code=item.source_code,
                    error_message=item.error_message,
                )
                session.merge(model)
            session.commit()

    def get_todo_items(
        self, iteration_id: str | None = None, status: TodoStatus | None = None
    ) -> list[TodoItemRecord]:
        with self.SessionLocal() as session:
            query = select(TodoItemModel)
            if iteration_id:
                query = query.where(TodoItemModel.iteration_id == iteration_id)
            if status:
                query = query.where(TodoItemModel.status == status.value)

            query = query.order_by(TodoItemModel.created_at)
            results = session.execute(query).scalars().all()

            records = []
            for r in results:
                citations_val = r.citations
                if citations_val:
                    try:
                        citations_val = json.loads(citations_val)
                    except Exception:
                        pass

                records.append(
                    TodoItemRecord(
                        id=r.id,
                        iteration_id=r.iteration_id,
                        section_path=r.section_path,
                        title=r.title,
                        kind=r.kind,
                        purpose=r.purpose,
                        what_to_cover=r.what_to_cover,
                        citations=citations_val,
                        status=TodoStatus(r.status),
                        source_code=r.source_code,
                        error_message=r.error_message,
                        created_at=r.created_at,
                        updated_at=r.updated_at,
                    )
                )
            return records

    def update_todo_status(
        self,
        item_id: str,
        status: TodoStatus,
        source_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.SessionLocal() as session:
            item = session.get(TodoItemModel, item_id)
            if item:
                item.status = status.value
                if source_code is not None:
                    item.source_code = source_code
                if error_message is not None:
                    item.error_message = error_message
                item.updated_at = datetime.now(timezone.utc)
                session.commit()

    # --- Feedback and Flywheel Learning ---

    def add_feedback(self, feedback: FeedbackRecord) -> FeedbackRecord:
        with self.SessionLocal() as session:
            model = FeedbackModel(
                iteration_id=feedback.iteration_id,
                phase=feedback.phase.value,
                user_feedback=feedback.user_feedback,
                agent_reflection=feedback.agent_reflection,
                learned_rule=feedback.learned_rule,
            )
            session.add(model)
            session.commit()
            feedback.id = model.id
            return feedback

    def get_learned_rules(self, phase: PhaseType | None = None) -> list[str]:
        with self.SessionLocal() as session:
            query = select(FeedbackModel).where(FeedbackModel.learned_rule.isnot(None))
            if phase:
                query = query.where(FeedbackModel.phase == phase.value)
            results = session.execute(query).scalars().all()
            return [r.learned_rule for r in results if r.learned_rule]

    def get_all_feedback(self) -> list[FeedbackRecord]:
        with self.SessionLocal() as session:
            results = session.execute(
                select(FeedbackModel).order_by(FeedbackModel.created_at.desc())
            ).scalars().all()
            return [
                FeedbackRecord(
                    id=r.id,
                    iteration_id=r.iteration_id,
                    phase=PhaseType(r.phase),
                    user_feedback=r.user_feedback,
                    agent_reflection=r.agent_reflection,
                    learned_rule=r.learned_rule,
                    created_at=r.created_at,
                )
                for r in results
            ]

    # --- Mathlingua Gaps ---

    def record_gap(self, gap: GapRecord) -> GapRecord:
        with self.SessionLocal() as session:
            model = GapModel(
                item_id=gap.item_id,
                concept=gap.concept,
                description=gap.description,
                attempted_representation=gap.attempted_representation,
                user_guidance=gap.user_guidance,
                resolved=gap.resolved,
            )
            session.add(model)
            session.commit()
            gap.id = model.id
            return gap

    def get_unresolved_gaps(self) -> list[GapRecord]:
        with self.SessionLocal() as session:
            results = session.execute(
                select(GapModel).where(GapModel.resolved.is_(False))
            ).scalars().all()
            return [
                GapRecord(
                    id=r.id,
                    item_id=r.item_id,
                    concept=r.concept,
                    description=r.description,
                    attempted_representation=r.attempted_representation,
                    user_guidance=r.user_guidance,
                    resolved=r.resolved,
                    created_at=r.created_at,
                )
                for r in results
            ]

    def resolve_gap(self, gap_id: int, user_guidance: str) -> None:
        with self.SessionLocal() as session:
            gap = session.get(GapModel, gap_id)
            if gap:
                gap.resolved = True
                gap.user_guidance = user_guidance
                session.commit()

    # --- Golden Test Records ---

    def save_golden(self, golden: GoldenRecord) -> None:
        with self.SessionLocal() as session:
            model = GoldenModel(
                id=golden.id,
                name=golden.name,
                prompt=golden.prompt,
                plan_summary=golden.plan_summary,
                expected_symbols=json.dumps(golden.expected_symbols),
                expected_source=golden.expected_source,
                citations=json.dumps(golden.citations),
                file_path=golden.file_path,
            )
            session.merge(model)
            session.commit()

    def get_goldens(self) -> list[GoldenRecord]:
        with self.SessionLocal() as session:
            results = session.execute(select(GoldenModel)).scalars().all()
            records = []
            for r in results:
                symbols = json.loads(r.expected_symbols) if r.expected_symbols else []
                citations = json.loads(r.citations) if r.citations else []
                records.append(
                    GoldenRecord(
                        id=r.id,
                        name=r.name,
                        prompt=r.prompt,
                        plan_summary=r.plan_summary,
                        expected_symbols=symbols,
                        expected_source=r.expected_source,
                        citations=citations,
                        file_path=r.file_path,
                        created_at=r.created_at,
                    )
                )
            return records
