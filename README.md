Sync macOS Photos library to digital photo frames.

## Installation

Install Python via `pyenv`, configured with support for shared libraries. Without this, we will not be able to use `pyinstaller`.

```bash 
PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.10.2
```

Install ImageMagick via `brew`

```bash
brew install imagemagick
```

Build the `peopleframe` binary

```bash
poetry run pyinstaller ./peopleframe.spec
```

Install the `peopleframe` binary somewhere static, e.g.

```bash
mv dist/peopleframe ~/bin
```

Note that [apparently](https://developer.apple.com/forums/thread/130313) using
`cp` do this triggers a kernel bug where the previously-cached metadata for the
old binary will be used, causing the new one to fail signature checks. Using
`mv` works around this. Presumably a reboot would as well?

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
pyinstaller \
    -Fc --collect-all osxphotos --collect-all photoscript \
    ./peopleframe/main.py
```

### Run from `poetry`

During development it can be useful to run the application without triggering a full binary build. This can be done using `poetry`, e.g.

```bash
poetry run peopleframe -vvv -f ~/.peopleframe-random.ini
```

### Disabling HTTPS certificate validation

This can be useful when running against an HTTPS debugging proxy like [Charles](https://charlesproxy.com/) which self-signs its own certificates. Passing the `-k` flag to the `peopleframe` binary will disable this checking.
