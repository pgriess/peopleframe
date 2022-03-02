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
