"""
Simple npyscreen demo for MC2 evaluation
"""
import npyscreen


class MC2NpyscreenApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm("MAIN", MainForm, name="Maestro MC2 - Npyscreen Demo")
        
class MainForm(npyscreen.FormBaseNew):
    def create(self):
        # Create the layout: menubar, two panes, status bar
        self.menubar = self.add(npyscreen.TitleText, name="File Edit View Help", 
                                rely=0, relx=0, editable=False)
        
        # Left pane
        self.left_pane = self.add(npyscreen.BoxTitle, name="Sessions", 
                                  rely=1, relx=0, max_height=-3, max_width=50)
        self.left_pane.entry_widget = self.left_pane.add(npyscreen.MultiLine, 
                                                         values=["Session 1", "Session 2", "Session 3"])
        
        # Right pane  
        self.right_pane = self.add(npyscreen.BoxTitle, name="Session Details", 
                                   rely=1, relx=51, max_height=-3, max_width=-1)
        self.right_pane.entry_widget = self.right_pane.add(npyscreen.MultiLine, 
                                                           values=["Details for selected session"])
        
        # Status line
        self.status = self.add(npyscreen.TitleText, name="F1=Help F5=Refresh F10=Quit", 
                               rely=-2, relx=0, editable=False)
        
    def while_waiting(self):
        # Demo exits after 1 second
        import time
        time.sleep(1)
        self.parentApp.setNextForm(None)


def main():
    app = MC2NpyscreenApp()
    try:
        app.run()
    except:
        # If npyscreen is not available, just print a message
        print("npyscreen demo - would show two panes with status line")
        import time
        time.sleep(1)


if __name__ == "__main__":
    main()