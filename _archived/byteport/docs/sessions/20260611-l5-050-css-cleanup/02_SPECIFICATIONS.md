# Specifications

## Acceptance criteria

- Remove only CSS that is demonstrably unused.
- Do not alter live route styles or Storybook component styles.
- Record validation results and any unrelated failures.

## Assumptions

- Unreferenced files under `frontend/web/src/assets/css/` are not loaded dynamically outside the repository.

## Risks

- External consumers outside this repository could theoretically reference these assets by path.

## Mitigation

- Limit removal to files with zero in-repo references.
- Validate the frontend build/check pipeline after deletion.
