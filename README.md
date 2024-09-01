Sync macOS Photos library to digital photo frames.

## Building

### Install Python official site

The official Python site ships universal binaries. Install one; they end up in
e.g. `/Library/Frameworks/Python.framework/Versions/3.12/`.

### Set up a venv

Create and activate the venv
```bash
python3.12 -m venv venv
source venv/bin/activate
```

Install Poetry
```bash
pip3 install poetry==1.8.3
```

Then install our project
```bash
poetry install
```

```

### Build the `peopleframe` binary

```bash
poetry run pyinstaller ./peopleframe.spec
```

### Wrap the binary in a `PeopleFrame.app`

```
mkdir -p dist/PeopleFrame.app/Contents/MacOS
mv dist/peopleframe dist/PeopleFrame.app/Contents/MacOS/PeopleFrame
```

## Installation

### Install `PeopleFrame.app` somewhere static

```bash
rm -fr ~/Applications/PeopleFrame.app
cp -R dist/PeopleFrame.app ~/Applications/
ln -sf ~/Applications/PeopleFrame.app/Contents/MacOS/PeopleFrame ~/bin/peopleframe
```

### Grant the `PeopleFrame.app` Full Disk access

Open the "System Settings" macOS application, search for "Privacy & Security", then selected "Full Disk Access". Click the little "+" icon at the bottom left of the list, navigate to ~/Applications and select "PeopleFrame".

Reboot your computer.

### Install a launch agent

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

### How to update a launch agent

```bash
launchctl bootout gui/$UID/ ~/Library/LaunchAgents/in.std.peopleframe.plist
cp in.std.peopleframe.plist ~/Library/LaunchAgents
launchctl bootstrap gui/$UID/ ~/Library/LaunchAgents/in.std.peopleframe.plist
```

### How to see details of a launch agent

```bash
launchctl print gui/$UID/in.std.peopleframe
```

### Run from `poetry`

During development it can be useful to run the application without triggering a full binary build. This can be done using `poetry`, e.g.

```bash
poetry run peopleframe -vvv -f ~/.peopleframe-random.ini
```

### Disabling HTTPS certificate validation

This can be useful when running against an HTTPS debugging proxy like [Charles](https://charlesproxy.com/) which self-signs its own certificates. Passing the `-k` flag to the `peopleframe` binary will disable this checking.
