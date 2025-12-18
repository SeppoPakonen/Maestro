"""Terminal-based discussion mode."""

from __future__ import annotations

from typing import List

from .discussion import Discussion, DiscussionResult


class TerminalDiscussion(Discussion):
    """Discussion loop in the terminal."""

    def start(self) -> DiscussionResult:
        print("[System] Enter /done to finish, /quit to cancel, /help for help.")
        while True:
            try:
                user_input = self._read_input()
            except KeyboardInterrupt:
                print("\n[System] Cancelled.")
                self.completed = False
                break
            if not user_input:
                continue
            if self.process_command(user_input):
                print("[System] Exiting discussion.")
                break
            if user_input.strip().lower() == "/help":
                self._print_help()
                continue

            self.add_user_message(user_input)
            print("AI: ...")
            response = self.ai_client.send_message(self.messages, self.context.system_prompt)
            self.add_ai_message(response)
            print(f"AI: {response}")

        return DiscussionResult(
            messages=self.messages,
            actions=self.actions,
            completed=self.completed,
        )

    def _read_input(self) -> str:
        lines: List[str] = []
        prompt = "You: "
        while True:
            line = input(prompt)
            if line.endswith("\\"):
                lines.append(line[:-1])
                prompt = "... "
                continue
            lines.append(line)
            break
        return "\n".join(lines).strip()

    def _print_help(self) -> None:
        print("[System] Commands:")
        print("  /done  - finish and apply actions")
        print("  /quit  - cancel discussion")
        print("  /help  - show this help")
        print("  Use '\\' at end of a line to continue input.")
