# CLI Surface Audit Report

**Generated:** 2025-12-28 12:56:37 UTC

**Purpose:** Compare actual CLI command surface (from code parser) against canonical runbook-extracted command list.

**Policy:** [Test Command Truth Policy](test_command_truth_policy.md)

**Canonical Commands:** `allowed_commands.normalized.txt`

---

## Summary

- ✅ In both code and runbooks: 28 commands
- ⚠️  In code but NOT in runbooks: 641 commands
- ❌ In runbooks but NOT in code: 33 commands

---

## ✅ In Both Code and Runbooks

These commands are properly aligned between implementation and documentation.

```
maestro ai claude
maestro ai codex
maestro ai gemini
maestro ai qwen
maestro build
maestro convert new
maestro convert plan
maestro convert run
maestro discuss
maestro init
maestro issues list
maestro phase add
maestro repo conf
maestro repo conventions
maestro repo resolve
maestro repo show
maestro rules list
maestro runbook add
maestro runbook export
maestro runbook step-add
maestro settings set
maestro task add
maestro track add
maestro tu build
maestro tu query
maestro work task
maestro wsession breadcrumb
maestro wsession show
```

---

## ⚠️ In Code But NOT in Runbooks

**These commands exist in the code but are NOT documented in runbooks.**

**Possible reasons:**
1. Legacy commands that should be deprecated/removed
2. New commands that need runbook documentation
3. Aliases or internal commands not meant for users

**Action Required:**
- Review each command
- If legacy (e.g., `session`, `understand`, `resume`, `rules`), consider deprecation
- If new and valid, add to runbooks and re-extract allowed commands
- If internal/alias, document why it's not in runbooks

```
maestro ai
maestro ai h
maestro ai help
maestro ai qwen-old
maestro ai sync
maestro build a
maestro build an
maestro build analyze
maestro build android
maestro build b
maestro build build
maestro build c
maestro build cfg
maestro build clean
maestro build config
maestro build exp
maestro build export
maestro build j
maestro build jar
maestro build methods
maestro build mth
maestro build r
maestro build rebuild
maestro c
maestro c b
maestro c batch
maestro c n
maestro c new
maestro c p
maestro c plan
maestro c r
maestro c reset
maestro c rst
maestro c run
maestro c s
maestro c sh
maestro c show
maestro c status
maestro cfg
maestro cfg e
maestro cfg edit
maestro cfg g
maestro cfg get
maestro cfg h
maestro cfg help
maestro cfg l
maestro cfg list
maestro cfg ls
maestro cfg pr
maestro cfg prof
maestro cfg profile
maestro cfg r
maestro cfg reset
maestro cfg s
maestro cfg set
maestro cfg w
maestro cfg wizard
maestro config
maestro config e
maestro config edit
maestro config g
maestro config get
maestro config h
maestro config help
maestro config l
maestro config list
maestro config ls
maestro config pr
maestro config prof
maestro config profile
maestro config r
maestro config reset
maestro config s
maestro config set
maestro config w
maestro config wizard
maestro convert
maestro convert b
maestro convert batch
maestro convert n
maestro convert p
maestro convert r
maestro convert reset
maestro convert rst
maestro convert s
maestro convert sh
maestro convert show
maestro convert status
maestro discuss replay
maestro discuss resume
maestro h
maestro help
maestro issues
maestro issues analyze
maestro issues build
maestro issues convention
maestro issues decide
maestro issues features
maestro issues fix
maestro issues hier
maestro issues look
maestro issues ls
maestro issues product
maestro issues react
maestro issues rollback
maestro issues runtime
maestro issues show
maestro issues state
maestro issues ux
maestro lg
maestro lg list
maestro lg list-plan
maestro lg list-work
maestro lg lp
maestro lg ls
maestro lg lw
maestro log
maestro log list
maestro log list-plan
maestro log list-work
maestro log lp
maestro log ls
maestro log lw
maestro m
maestro m a
maestro m an
maestro m analyze
maestro m android
maestro m b
maestro m build
maestro m c
maestro m cfg
maestro m clean
maestro m config
maestro m exp
maestro m export
maestro m j
maestro m jar
maestro m methods
maestro m mth
maestro m r
maestro m rebuild
maestro make
maestro make a
maestro make an
maestro make analyze
maestro make android
maestro make b
maestro make build
maestro make c
maestro make cfg
maestro make clean
maestro make config
maestro make exp
maestro make export
maestro make j
maestro make jar
maestro make methods
maestro make mth
maestro make r
maestro make rebuild
maestro ops
maestro ops apply
maestro ops preview
maestro ops validate
maestro p
maestro p a
maestro p add
maestro p d
maestro p discuss
maestro p e
maestro p edit
maestro p h
maestro p help
maestro p l
maestro p list
maestro p ls
maestro p r
maestro p raw
maestro p remove
maestro p rm
maestro p set
maestro p set-status
maestro p set-text
maestro p setraw
maestro p sh
maestro p show
maestro p st
maestro p status
maestro p text
maestro ph
maestro ph a
maestro ph add
maestro ph d
maestro ph discuss
maestro ph e
maestro ph edit
maestro ph h
maestro ph help
maestro ph l
maestro ph list
maestro ph ls
maestro ph r
maestro ph raw
maestro ph remove
maestro ph rm
maestro ph set
maestro ph set-status
maestro ph set-text
maestro ph setraw
maestro ph sh
maestro ph show
maestro ph st
maestro ph status
maestro ph text
maestro phase
maestro phase a
maestro phase d
maestro phase discuss
maestro phase e
maestro phase edit
maestro phase h
maestro phase help
maestro phase l
maestro phase list
maestro phase ls
maestro phase r
maestro phase raw
maestro phase remove
maestro phase rm
maestro phase set
maestro phase set-status
maestro phase set-text
maestro phase setraw
maestro phase sh
maestro phase show
maestro phase st
maestro phase status
maestro phase text
maestro pl
maestro pl a
maestro pl add
maestro pl add-item
maestro pl ai
maestro pl d
maestro pl discuss
maestro pl e
maestro pl explore
maestro pl list
maestro pl ls
maestro pl ops
maestro pl remove
maestro pl remove-item
maestro pl ri
maestro pl rm
maestro pl sh
maestro pl show
maestro plan
maestro plan a
maestro plan add
maestro plan add-item
maestro plan ai
maestro plan d
maestro plan discuss
maestro plan e
maestro plan explore
maestro plan list
maestro plan ls
maestro plan ops
maestro plan remove
maestro plan remove-item
maestro plan ri
maestro plan rm
maestro plan sh
maestro plan show
maestro r
maestro r e
maestro r edit
maestro r list
maestro r ls
maestro rb
maestro rb add
maestro rb d
maestro rb delete
maestro rb discuss
maestro rb e
maestro rb edit
maestro rb exp
maestro rb export
maestro rb list
maestro rb ls
maestro rb new
maestro rb remove
maestro rb render
maestro rb rm
maestro rb rnd
maestro rb sa
maestro rb se
maestro rb sh
maestro rb show
maestro rb sr
maestro rb srn
maestro rb step-add
maestro rb step-edit
maestro rb step-renumber
maestro rb step-rm
maestro repo
maestro repo c
maestro repo h
maestro repo help
maestro repo hier
maestro repo pkg
maestro repo refresh
maestro repo res
maestro repo rules
maestro repo sh
maestro resume
maestro root
maestro root d
maestro root discuss
maestro root g
maestro root get
maestro root r
maestro root refine
maestro root s
maestro root set
maestro root sh
maestro root show
maestro rs
maestro rules
maestro rules e
maestro rules edit
maestro rules ls
maestro runba
maestro runba add
maestro runba d
maestro runba delete
maestro runba discuss
maestro runba e
maestro runba edit
maestro runba exp
maestro runba export
maestro runba list
maestro runba ls
maestro runba new
maestro runba remove
maestro runba render
maestro runba rm
maestro runba rnd
maestro runba sa
maestro runba se
maestro runba sh
maestro runba show
maestro runba sr
maestro runba srn
maestro runba step-add
maestro runba step-edit
maestro runba step-renumber
maestro runba step-rm
maestro runbook
maestro runbook d
maestro runbook delete
maestro runbook discuss
maestro runbook e
maestro runbook edit
maestro runbook exp
maestro runbook list
maestro runbook ls
maestro runbook new
maestro runbook remove
maestro runbook render
maestro runbook rm
maestro runbook rnd
maestro runbook sa
maestro runbook se
maestro runbook sh
maestro runbook show
maestro runbook sr
maestro runbook srn
maestro runbook step-edit
maestro runbook step-renumber
maestro runbook step-rm
maestro s
maestro s bc
maestro s breadcrumbs
maestro s d
maestro s details
maestro s g
maestro s get
maestro s l
maestro s list
maestro s ls
maestro s n
maestro s new
maestro s remove
maestro s rm
maestro s set
maestro s st
maestro s stats
maestro s stt
maestro s timeline
maestro s tl
maestro session
maestro session bc
maestro session breadcrumbs
maestro session d
maestro session details
maestro session g
maestro session get
maestro session l
maestro session list
maestro session ls
maestro session n
maestro session new
maestro session remove
maestro session rm
maestro session set
maestro session st
maestro session stats
maestro session stt
maestro session timeline
maestro session tl
maestro settings
maestro settings e
maestro settings edit
maestro settings g
maestro settings get
maestro settings h
maestro settings help
maestro settings l
maestro settings list
maestro settings ls
maestro settings pr
maestro settings prof
maestro settings profile
maestro settings r
maestro settings reset
maestro settings s
maestro settings w
maestro settings wizard
maestro solutions
maestro solutions add
maestro solutions edit
maestro solutions list
maestro solutions ls
maestro solutions remove
maestro solutions rm
maestro solutions show
maestro t
maestro t a
maestro t add
maestro t d
maestro t details
maestro t discuss
maestro t dt
maestro t e
maestro t edit
maestro t h
maestro t help
maestro t l
maestro t list
maestro t ls
maestro t r
maestro t raw
maestro t remove
maestro t rm
maestro t s
maestro t set
maestro t set-status
maestro t set-text
maestro t setraw
maestro t sh
maestro t show
maestro t st
maestro t status
maestro t text
maestro ta
maestro ta a
maestro ta add
maestro ta d
maestro ta discuss
maestro ta h
maestro ta help
maestro ta l
maestro ta list
maestro ta ls
maestro ta r
maestro ta raw
maestro ta remove
maestro ta rm
maestro ta set-status
maestro ta set-text
maestro ta setraw
maestro ta sh
maestro ta show
maestro ta status
maestro ta text
maestro task
maestro task a
maestro task d
maestro task discuss
maestro task h
maestro task help
maestro task l
maestro task list
maestro task ls
maestro task r
maestro task raw
maestro task remove
maestro task rm
maestro task set-status
maestro task set-text
maestro task setraw
maestro task sh
maestro task show
maestro task status
maestro task text
maestro tr
maestro tr a
maestro tr add
maestro tr d
maestro tr details
maestro tr discuss
maestro tr dt
maestro tr e
maestro tr edit
maestro tr h
maestro tr help
maestro tr l
maestro tr list
maestro tr ls
maestro tr r
maestro tr raw
maestro tr remove
maestro tr rm
maestro tr s
maestro tr set
maestro tr set-status
maestro tr set-text
maestro tr setraw
maestro tr sh
maestro tr show
maestro tr st
maestro tr status
maestro tr text
maestro track
maestro track a
maestro track d
maestro track details
maestro track discuss
maestro track dt
maestro track e
maestro track edit
maestro track h
maestro track help
maestro track l
maestro track list
maestro track ls
maestro track r
maestro track raw
maestro track remove
maestro track rm
maestro track s
maestro track set
maestro track set-status
maestro track set-text
maestro track setraw
maestro track sh
maestro track show
maestro track st
maestro track status
maestro track text
maestro tu
maestro tu cache
maestro tu complete
maestro tu draft
maestro tu info
maestro tu lsp
maestro tu print-ast
maestro tu references
maestro tu transform
maestro u
maestro u d
maestro u dump
maestro understand
maestro understand d
maestro understand dump
maestro wk
maestro wk analyze
maestro wk any
maestro wk discuss
maestro wk fix
maestro wk issue
maestro wk phase
maestro wk task
maestro wk track
maestro work
maestro work analyze
maestro work any
maestro work discuss
maestro work fix
maestro work issue
maestro work phase
maestro work track
maestro workflow
maestro workflow create
maestro workflow delete
maestro workflow e
maestro workflow edit
maestro workflow list
maestro workflow ls
maestro workflow new
maestro workflow rm
maestro workflow sh
maestro workflow show
maestro workflow visualize
maestro workflow viz
maestro ws
maestro ws breadcrumb
maestro ws breadcrumbs
maestro ws close
maestro ws l
maestro ws list
maestro ws ls
maestro ws sh
maestro ws show
maestro ws stats
maestro ws timeline
maestro ws tr
maestro ws tree
maestro wsession
maestro wsession breadcrumbs
maestro wsession close
maestro wsession l
maestro wsession list
maestro wsession ls
maestro wsession sh
maestro wsession stats
maestro wsession timeline
maestro wsession tr
maestro wsession tree
```

---

## ❌ In Runbooks But NOT in Code

**These commands are documented in runbooks but don't exist in code.**

**This indicates:**
1. Commands removed from code but not from documentation
2. Commands not yet implemented
3. Potential typos in runbook documentation

**Action Required:**
- If removed, update runbooks to remove these commands
- If planned, implement them or mark as TODO in runbooks
- If typos, fix runbook documentation

```
maestro --help
maestro build --help
maestro convert --help
maestro discuss --engine
maestro discuss --resume
maestro init --greenfield
maestro init --read-only
maestro issues --help
maestro issues accept
maestro issues add
maestro issues ignore
maestro make --with-hub-deps
maestro ops commit
maestro repo --help
maestro repo hub
maestro rules --help
maestro rules check
maestro session log
maestro solutions match
maestro task complete
maestro tu --help
maestro tu autocomplete
maestro tu refactor
maestro work --resume
maestro work close
maestro work resume
maestro work spawn
maestro workflow accept
maestro workflow edge
maestro workflow init
maestro workflow node
maestro workflow render
maestro workflow validate
```

---

## Next Steps

1. Review "In code but NOT in runbooks" section
2. Document deprecation status for legacy commands (see `docs/workflows/v3/cli/DEPRECATION.md`)
3. Update runbooks or code to align the command surface
4. Re-run this audit after changes

