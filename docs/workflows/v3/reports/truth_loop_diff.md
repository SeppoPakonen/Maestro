# Truth Loop Diff Report

Comparison of runbook command usage vs CLI surface.

**Generated:** Run `python tools/truth_loop/compare.py` to regenerate.

---

## Summary

- ✅ **Both OK**: 24 commands aligned
- ⚠️ **Runbook Only**: 76 commands in runbooks but not CLI
- 📖 **CLI Only**: 609 commands in CLI but no runbook examples
- 🔄 **Needs Alias**: 0 commands using legacy forms
- 📝 **Needs Docs**: 559 commands missing runbook examples
- 🔧 **Needs Runbook Fix**: 0 deprecated command usage

---

## ⚠️ Runbook-Only Commands

Commands found in runbooks but not in CLI surface (default mode).

```
ai qwen "Explain
ai qwen session-001
convert add cpp-to-python
convert plan cpp-to-python
convert run cpp-to-python
discuss gemini
discuss resume session-20250126-001
issues accept issue-001
issues ignore issue-001
issues list blocker
issues list convention
make make MyApp
phase add track-001
platform caps detect
platform caps prefer
platform caps require
repo conventions check
repo resolve lite
repo show packages
runbook add "C++
runbook add "GUI
runbook add "Hello
runbook add "Text
runbook archive RB-001
runbook archive docs/workflows/v3/runbooks/examples/EX-01_old_example.sh
runbook export c-hello-program
runbook export hello-cli-tool
runbook export text-adventure-game-loop
runbook list json
runbook show RB-001
runbook step-add c-hello-program
runbook step-add gui-menu-edit
runbook step-add gui-menu-file
runbook step-add gui-menu-help
runbook step-add hello-cli-tool
runbook step-add text-adventure-game-loop
select toolchain detect
select toolchain export
select toolchain set
select toolchain show
settings set ai_stacking_mode
solutions check
solutions match
task add issue-001
task add phase-001
task complete task-001
track add "Sprint
tu autocomplete src/main.cpp
tu make target-cmake-mathapp
tu make target-upp-app
tu query symbol
tu refactor rename
work resume wsession-parent-abc123
work spawn task-001
work task task-001
work task task-002
workflow accept user-auth-service
workflow archive docs/workflows/v3/workflows/WF-OLD.md
workflow edge add
workflow init edit-menu-workflow
workflow init file-menu-workflow
workflow init game-loop-workflow
workflow init hello-cli-workflow
workflow init hello-cpp-workflow
workflow init user-auth-service
workflow node add
workflow render file-menu-workflow
workflow render hello-cli-workflow
workflow render puml
workflow show docs/workflows/v3/workflows/WF-OLD.md
workflow validate edit-menu-workflow
workflow validate file-menu-workflow
workflow validate game-loop-workflow
workflow validate hello-cli-workflow
workflow validate hello-cpp-workflow
wsession log session-20250126-001
```

**Action:** Verify these commands exist in CLI or update runbooks.

---

## 📖 CLI-Only Commands (Need Examples)

Commands in CLI surface but missing runbook examples.

### `ai` namespace

```
ai
ai qwen-old
ai sync
```

### `build` namespace

```
build
build an
build analyze
build android
build build
build cfg
build cfg detect
build cfg edit
build cfg list
build cfg show
build clean
build config
build config detect
build config edit
build config list
build config show
build exp
build export
build jar
build methods
build mth
build rebuild
build str
build str apply
build str fix
build str lint
build str sc
build str scan
build str show
build structure
build structure apply
build structure fix
build structure lint
build structure sc
build structure scan
build structure show
```

### `c` namespace

```
c add
c b rep
c b report
c b run
c b show
c b status
c batch
c batch rep
c batch report
c batch run
c batch show
c batch status
c new
c plan
c reset
c rst
c run
c show
c status
```

### `cache` namespace

```
cache
cache prune
cache show
cache stats
```

### `cfg` namespace

```
cfg
cfg edit
cfg get
cfg list
cfg pr
cfg pr get
cfg pr list
cfg pr load
cfg pr save
cfg pr sd
cfg pr set-default
cfg prof
cfg prof get
cfg prof list
cfg prof load
cfg prof save
cfg prof sd
cfg prof set-default
cfg profile
cfg profile get
cfg profile list
cfg profile load
cfg profile save
cfg profile sd
cfg profile set-default
cfg reset
cfg set
cfg wizard
```

### `config` namespace

```
config
config edit
config get
config list
config pr
config pr get
config pr list
config pr load
config pr save
config pr sd
config pr set-default
config prof
config prof get
config prof list
config prof load
config prof save
config prof sd
config prof set-default
config profile
config profile get
config profile list
config profile load
config profile save
config profile sd
config profile set-default
config reset
config set
config wizard
```

### `convert` namespace

```
convert add
convert b rep
convert b report
convert b run
convert b show
convert b status
convert batch
convert batch rep
convert batch report
convert batch run
convert batch show
convert batch status
convert new
convert plan
convert reset
convert rst
convert run
convert show
convert status
```

### `discuss` namespace

```
discuss replay
discuss resume
```

### `issues` namespace

```
issues add
issues analyze
issues build
issues convention
issues decide
issues features
issues fix
issues hier
issues ignore
issues link-task
issues look
issues product
issues react
issues resolve
issues rollback
issues runtime
issues show
issues state
issues triage
issues ux
```

### `log` namespace

```
log
log scan
log show
```

### `m` namespace

```
m an
m analyze
m android
m build
m cfg
m cfg detect
m cfg edit
m cfg list
m cfg show
m clean
m config
m config detect
m config edit
m config list
m config show
m exp
m export
m jar
m methods
m mth
m rebuild
m str
m str apply
m str fix
m str lint
m str sc
m str scan
m str show
m structure
m structure apply
m structure fix
m structure lint
m structure sc
m structure scan
m structure show
```

### `make` namespace

```
make an
make analyze
make android
make build
make cfg
make cfg detect
make cfg edit
make cfg list
make cfg show
make clean
make config
make config detect
make config edit
make config list
make config show
make exp
make export
make jar
make methods
make mth
make rebuild
make str
make str apply
make str fix
make str lint
make str sc
make str scan
make str show
make structure
make structure apply
make structure fix
make structure lint
make structure sc
make structure scan
make structure show
```

### `p` namespace

```
p add
p discuss
p edit
p list
p raw
p remove
p set
p set-status
p set-text
p setraw
p show
p st
p status
p text
```

### `ph` namespace

```
ph
ph add
ph discuss
ph edit
ph list
ph raw
ph remove
ph set
ph set-status
ph set-text
ph setraw
ph show
ph st
ph status
ph text
```

### `phase` namespace

```
phase
phase add
phase discuss
phase edit
phase list
phase raw
phase remove
phase set
phase set-status
phase set-text
phase setraw
phase show
phase st
phase status
phase text
```

### `pl` namespace

```
pl
pl add
pl add-item
pl ai
pl discuss
pl explore
pl list
pl ops
pl ops apply
pl ops preview
pl ops validate
pl remove
pl remove-item
pl ri
pl show
```

### `rb` namespace

```
rb
rb add
rb archive
rb delete
rb discuss
rb edit
rb exp
rb export
rb list
rb new
rb remove
rb render
rb restore
rb rnd
rb sa
rb se
rb show
rb sr
rb srn
rb step-add
rb step-edit
rb step-renumber
rb step-rm
```

### `repo` namespace

```
repo c list
repo c select-default
repo c show
repo conf
repo conf list
repo conf select-default
repo conf show
repo conventions
repo conventions detect
repo conventions show
repo hier
repo hier edit
repo hier show
repo hub
repo hub find package
repo hub find pkg
repo hub link package
repo hub link pkg
repo hub link remove
repo hub link show
repo hub scan
repo pkg
repo refresh
repo res
repo rules
repo rules edit
repo rules inject
repo rules show
repo show
```

### `runba` namespace

```
runba
runba add
runba archive
runba delete
runba discuss
runba edit
runba exp
runba export
runba list
runba new
runba remove
runba render
runba restore
runba rnd
runba sa
runba se
runba show
runba sr
runba srn
runba step-add
runba step-edit
runba step-renumber
runba step-rm
```

### `runbook` namespace

```
runbook
runbook add
runbook archive
runbook delete
runbook discuss
runbook edit
runbook exp
runbook export
runbook new
runbook remove
runbook render
runbook restore
runbook rnd
runbook sa
runbook se
runbook show
runbook sr
runbook srn
runbook step-add
runbook step-edit
runbook step-renumber
runbook step-rm
```

### `settings` namespace

```
settings
settings edit
settings get
settings list
settings pr
settings pr get
settings pr list
settings pr load
settings pr save
settings pr sd
settings pr set-default
settings prof
settings prof get
settings prof list
settings prof load
settings prof save
settings prof sd
settings prof set-default
settings profile
settings profile get
settings profile list
settings profile load
settings profile save
settings profile sd
settings profile set-default
settings reset
settings set
settings wizard
```

### `solutions` namespace

```
solutions add
solutions edit
solutions remove
solutions show
```

### `t` namespace

```
t add
t details
t discuss
t dt
t edit
t list
t raw
t remove
t set
t set-status
t set-text
t setraw
t show
t st
t status
t text
```

### `ta` namespace

```
ta
ta add
ta discuss
ta list
ta raw
ta remove
ta set-status
ta set-text
ta setraw
ta show
ta status
ta text
```

### `task` namespace

```
task
task add
task discuss
task list
task raw
task remove
task set-status
task set-text
task setraw
task show
task status
task text
```

### `tr` namespace

```
tr
tr add
tr details
tr discuss
tr dt
tr edit
tr list
tr raw
tr remove
tr set
tr set-status
tr set-text
tr setraw
tr show
tr st
tr status
tr text
```

### `track` namespace

```
track
track add
track details
track discuss
track dt
track edit
track list
track raw
track remove
track set
track set-status
track set-text
track setraw
track show
track st
track status
track text
```

### `tu` namespace

```
tu build
tu cache
tu cache clear
tu cache stats
tu complete
tu draft
tu info
tu lsp
tu print-ast
tu query
tu references
tu transform
```

### `wk` namespace

```
wk
wk analyze
wk any
wk any pick
wk discuss
wk fix
wk issue
wk phase
wk resume
wk task
wk track
```

### `work` namespace

```
work
work analyze
work any
work any pick
work discuss
work fix
work issue
work phase
work resume
work task
work track
```

### `workflow` namespace

```
workflow
workflow archive
workflow create
workflow delete
workflow edit
workflow new
workflow restore
workflow show
workflow visualize
workflow viz
```

### `ws` namespace

```
ws
ws breadcrumb
ws breadcrumb add
ws breadcrumbs
ws close
ws list
ws show
ws stats
ws timeline
ws tr
ws tree
```

### `wsession` namespace

```
wsession
wsession breadcrumb
wsession breadcrumbs
wsession close
wsession list
wsession show
wsession stats
wsession timeline
wsession tr
wsession tree
```

**Action:** Create runbook examples for these commands.

---

## 🔄 Alias Coverage

Commands using legacy forms that need alias mapping verification.

*None*

**Action:** Verify aliases exist and update runbooks to use canonical forms.

---

## 🔧 Debt Table (Deprecated Usage)

Runbook commands using deprecated forms.

*None*

**Action:** Update runbooks to use canonical command forms.

---

## ✅ Aligned Commands

24 commands are properly aligned between runbooks and CLI.

</details>

