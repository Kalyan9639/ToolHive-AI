## ⚠️ One Small Risk

You are not preventing duplicate slugs.

If two tools have similar titles:
```
AI Writer
AI-Writer
```

Both become:
```
ai-writer
```

That will break matching later.

You should:

- either append short hash

- or skip if slug already exists in CSV