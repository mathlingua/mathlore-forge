# How Do I Add A Type Or Structure?

1. Search for the concept, intended command signature, components, and notation.
2. Choose the page where prerequisite commands are already explained.
3. Read [`Declares:`](../../mathlingua-structural-language/references/declares.md),
   [forms and declarations](../../mathlingua-formulation-language/references/forms-and-declarations.md),
   and [`specifies:`](../../mathlingua-support-sections/references/specifies.md).
4. Define the heading, target shape, parameter requirements, carried component
   facts, laws, and documentation.

```text
[\pointed.set]
Declares: P ::= (X, p)
specifies:
. X is \set
. p "in" X
Documented:
. called: "pointed set"
. description: "A set with a distinguished element."
```

Omit `Id:`, run the checker, retain its generated UUID, and review rendering.

## Do not

- Do not invent component names inconsistent with neighboring structures.
- Do not put laws that are proposition clauses into component assignments.
- Do not forget parameter `when:` facts or duplicate a signature.
- Do not declare a concrete distinguished object when the goal is a reusable type.
