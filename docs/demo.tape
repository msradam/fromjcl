# VHS tape for fromjcl CLI demo.
# Render from repo root: vhs docs/demo.tape   (writes docs/demo.gif)

Output docs/demo.gif

Set FontSize 16
Set Width 1100
Set Height 720
Set Theme "Catppuccin Mocha"
Set PlaybackSpeed 1.0
Set TypingSpeed 60ms
Set Padding 24
Set Margin 20
Set MarginFill "#1e1e2e"

Hide
Type "cd docs" Enter
Type "clear" Enter
Show

Type "# A small JCL job, allocate a PDS"
Sleep 600ms
Enter
Type "cat sample.jcl"
Sleep 400ms
Enter
Sleep 1500ms

Type "# Parse + emit as YAML"
Sleep 500ms
Enter
Type "fromjcl sample.jcl --to yaml"
Sleep 400ms
Enter
Sleep 2500ms

Type "# Same job as a ZOAU shell script"
Sleep 500ms
Enter
Type "fromjcl sample.jcl --to zoau"
Sleep 400ms
Enter
Sleep 2500ms

Type "# Pull every dataset DSN with jq"
Sleep 500ms
Enter
Type `fromjcl sample.jcl --to json | jq -r '.steps[].dds[].datasets[]?.dsn'`
Sleep 400ms
Enter
Sleep 2000ms

Type "# Byte-exact roundtrip back to JCL"
Sleep 500ms
Enter
Type "fromjcl sample.jcl --to jcl | diff - sample.jcl && echo OK"
Sleep 400ms
Enter
Sleep 2000ms
