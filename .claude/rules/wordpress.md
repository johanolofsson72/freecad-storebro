---
paths:
  - "**/*.php"
  - "wp-content/**"
---

# WordPress rules

- Follow WordPress Coding Standards.
- Never modify core files — use child themes, hooks, and filters.
- Use `$wpdb->prepare()` for database queries — never raw SQL.
- Never use `eval()` or `extract()`.
- Escape all output with `esc_html()`, `esc_attr()`, `esc_url()`.
