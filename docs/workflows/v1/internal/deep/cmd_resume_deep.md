@startuml cmd_resume_deep
!include _shared.puml

' Core Command Modules
MODULE(MaestroMain, "maestro/main.py") {
    FUNCTION(MainEntry, "main()")
}

MODULE(CommandHandlers, "maestro/modules/command_handlers.py") {
    FUNCTION(HandleResumeSession, "handle_resume_session()")
    FUNCTION(LoadSession, "load_session()")
    FUNCTION(SaveSession, "save_session()")
    FUNCTION(UpdateSubtaskSummaryPaths, "update_subtask_summary_paths()")
    FUNCTION(HasLegacyPlan, "has_legacy_plan()")
    FUNCTION(MigrateSessionIfNeeded, "migrate_session_if_needed()")
    FUNCTION(LoadRules, "load_rules()")
    FUNCTION(GetMaestroDir, "get_maestro_dir()")
    FUNCTION(BuildPrompt, "build_prompt()")
    FUNCTION(SavePromptForTraceability, "save_prompt_for_traceability()")
    FUNCTION(SaveAiOutput, "save_ai_output()")
    FUNCTION(LogVerbose, "log_verbose()")
}

' Session Model & Persistence
MODULE(SessionModel, "maestro/session_model.py") {
    CLASS(SessionClass, "Session")
    CLASS(SubtaskClass, "Subtask")
    CLASS(PlanNodeClass, "PlanNode")
}

' AI Engine Integration
MODULE(EnginesModule, "maestro/engines.py") {
    FUNCTION(GetEngine, "get_engine()")
    CLASS(EngineError, "EngineError")
}

' Utility Modules
MODULE(MaestroUtils, "maestro/modules/utils.py") {
    ' print_error, print_info etc.
}

' External Dependencies
ACTOR(FileSystem, "File System")
ACTOR(ExternalAI, "External AI Service")
ACTOR(Subprocess, "subprocess module") ' Implied by Engine interaction

' Persistent Stores
DATABASE(DocsSessionsDir, "docs/sessions/<name>/") {
    session.json
    rules.txt
    partials/worker_*.partial.txt
    inputs/worker_*.prompt.txt
    outputs/worker_*.stdout.txt
    outputs/<subtask.id>.summary.txt
}


' --- Relationships and Call Flow ---

' CLI Command Setup (implicit via maestro.main.py and cli_parser)

' Command Dispatch (from maestro.main.py)
MainEntry -- HandleResumeSession

' Session Loading and Migration
HandleResumeSession --> CommandHandlers.LoadSession --> DocsSessionsDir : "loads session.json"
HandleResumeSession --> CommandHandlers.UpdateSubtaskSummaryPaths : "updates summary paths"
HandleResumeSession --> CommandHandlers.HasLegacyPlan : "checks for legacy plan"
HandleResumeSession --> CommandHandlers.MigrateSessionIfNeeded : "migrates session"

' Rules Loading
HandleResumeSession --> CommandHandlers.LoadRules --> DocsSessionsDir : "loads rules.txt"

' Subtask Selection
HandleResumeSession --> SessionClass : "filters subtasks (pending/interrupted)"

' Directory Setup
HandleResumeSession --> CommandHandlers.GetMaestroDir
CommandHandlers.GetMaestroDir --> FileSystem : "creates inputs, outputs, partials dirs"

' Subtask Processing Loop
LOOP "For each target subtask"
    HandleResumeSession --> FileSystem : "reads partials/worker_*.partial.txt"
    HandleResumeSession --> CommandHandlers.BuildPrompt : "builds AI prompt"
    HandleResumeSession --> CommandHandlers.GetEngine : "gets AI worker engine"
    HandleResumeSession --> CommandHandlers.SavePromptForTraceability --[#Red,dashed]-> DocsSessionsDir : "saves prompt"
    HandleResumeSession --> ExternalAI : "invokes AI engine (engine.generate(prompt))"
    HandleResumeSession --> HandleInterrupt : "handles KeyboardInterrupt"
    HandleResumeSession --> HandleEngineError : "handles EngineError"
    HandleResumeSession --[#Red,dashed]-> DocsSessionsDir : "saves partial output on interrupt"
    HandleResumeSession --[#Red,dashed]-> DocsSessionsDir : "saves AI output (stdout.txt)"
    HandleResumeSession --> FileSystem : "verifies summary file existence/size"
    HandleResumeSession --> SessionClass : "updates subtask status to 'done'"
    HandleResumeSession --> CommandHandlers.SaveSession --[#Red,dashed]-> DocsSessionsDir : "saves updated session"
END LOOP

' Final Session Status Update
HandleResumeSession --> SessionClass : "updates overall session status"
HandleResumeSession --> CommandHandlers.SaveSession --[#Red,dashed]-> DocsSessionsDir : "saves final session state"

' Error & Interruption Handling
HandleInterrupt <-- ExternalAI : "User interrupt during AI generation"
HandleEngineError <-- ExternalAI : "AI engine failure"

HandleInterrupt --> DocsSessionsDir : "saves partial state"
HandleEngineError --> DocsSessionsDir : "saves error output"

' Data Model interactions
SessionClass <.. LoadSession : "loaded into"
SessionClass --> SaveSession : "saved from"
SubtaskClass <.. SessionClass : "accessed for processing"
PlanNodeClass <.. SessionClass : "accessed for active plan"

' Data Persistence
DocsSessionsDir <--> FileSystem : "reads/writes session.json, logs, partials, prompts, outputs"

@enduml