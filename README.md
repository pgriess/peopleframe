Sync macOS Photos library to digital photo frames.

## Installation

Build the `peopleframe` binary

```bash
poetry run pyinstaller ./peopleframe.spec
```

Copy the `peopleframe` binary somewhere static, e.g.

```bash
cp dist/peopleframe ~/bin
```

Install a launch agent.

To do this, we are going to use the `in.std.peopleframe.XXXXX.plist` file as a
template so that we can, e.g. run multiple instances of `peopleframe`
synchronizing different albums at different frequencies. Update it as follows

- Pick a unique filename by replacing `XXXXX`. In the rest of this example we use `LABEL`. Make sure that the `Label` property in the plist matches as well as any paths in other keys like `StandardErrorPath`. Make sure that the directories referenced in the various paths exist.

- Set the first element of the `ProgramArguments` array to the path where you installed the `peopleframe` binary, e.g.

```xml
<key>ProgramArguments</key>
<array>
    <string>/Users/pg/bin/peopleframe</string>
    ...
</array>
```

- Copy the resulting `in.std.peopleframe.LABEL.plist` file to `~/Library/LaunchAgents`

```bash
cp in.std.peopleframe.LABEL.plist ~/Library/LaunchAgents
```

- Load the agent

```bash
launchctl bootstrap gui/$UID/ ~/Library/LaunchAgents/in.std.peopleframe.LABEL.plist
```

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
