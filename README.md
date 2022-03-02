Sync macOS Photos library to digital photo frames.

## Developer notes

To update `in.std.peopleframe.plist` do this

```bash
launchctl bootout gui/$UID/ ~/Library/LaunchAgents/in.std.peopleframe.plist
cp in.std.peopleframe.plist ~/Library/LaunchAgents
launchctl bootstrap gui/$UID/ ~/Library/LaunchAgents/in.std.peopleframe.plist
```

To show details about the agent

```bash
launchctl print gui/$UID/in.std.peopleframe
```

To build the binary

```bash
poetry run pyinstaller peopleframe.spec
```

This spec file was generated as a by-product of running the following. Without
the extra `--collect-all` options, various resources were missing.

```bash
pyinstaller -Fc --collect-all osxphotos --collect-all photoscript ./peopleframe/main.py
```
