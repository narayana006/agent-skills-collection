# agent-skills-collection

A curated collection of reusable agent skills (SKILL.md) for release notes, migrations, security reviews, SEO and App Store audits.

> **Project status: planning. There is no working code in this repository yet.**
> This README describes what the project will do. Nothing below can be installed or run today.
> Features are ticked off in the checklist as they are built.

## What it is

A collection of Markdown skills and scripts.

**The problem it solves:** Good agent workflows live in people's heads or private notes. Skills make them repeatable and shareable.

## Who it is for

People who use AI coding agents and want proven, repeatable workflows instead of rewriting the same instructions.

## How it will work

1. Each skill is a folder with a SKILL.md file: when to use it, the steps to follow and any helper scripts.
2. You copy the skills you want into your agent's skills directory.
3. The agent loads a skill when a task matches it and follows the steps.

## Planned features

Unticked items are not built yet.

- [ ] Release-notes writer from git history
- [ ] Dependency / framework migration helper
- [ ] Security pre-merge checklist
- [ ] SEO audit for static and Next.js sites
- [ ] iOS App Store pre-submit audit (common rejection reasons)
- [ ] Template and guide for writing your own skill

## Planned usage

This is the intended interface, shown so you can judge the design. **It does not work yet**, and names may change before the first release.

```bash
cp -r skills/release-notes <your-agent-skills-dir>/
```

## Contributing

Feedback on the design is the most useful contribution right now. Open an issue to suggest a feature, question an approach or describe your use case. Code contributions are welcome once the first version lands.

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
