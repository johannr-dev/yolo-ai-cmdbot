

import os
import sys
import subprocess
import platform
import pyperclip
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static, TextArea
from textual.reactive import reactive
from textual import events
from textual.binding import Binding

from ai_model import AIModel
import yaml
import dotenv
import distro

class YoloApp(App):
    """A Textual UI for the yolo-ai-cmdbot."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
        height: 1fr;
        margin: 1 1;
    }
    
        height: 2fr;
        margin: 1 1;
    }
    
        height: auto;
        margin: 1 1;
        align: center middle;
    }
    
    .button {
        margin: 1 2;
    }
    
    TextArea {
        border: solid $primary;
    }
    
        height: 100%;
    }
    
        height: 100%;
    }
    
        height: auto;
        background: $primary;
        color: $text;
        padding: 1 2;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "submit", "Submit"),
        Binding("ctrl+e", "execute", "Execute"),
        Binding("ctrl+c", "copy", "Copy"),
    ]
    
    config = reactive({})
    shell = reactive("")
    
    def __init__(self):
        super().__init__()
        self.load_config()
        self.setup_shell()
        self.client = AIModel.get_model_client(self.config)
    
    def load_config(self):
        """Load configuration from yolo.yaml."""
        dotenv.load_dotenv()
        
        yolo_path = os.path.abspath(__file__)
        prompt_path = os.path.dirname(yolo_path)
        
        config_file = os.path.join(prompt_path, "yolo.yaml")
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
    
    def setup_shell(self):
        """Set up the shell based on the OS."""
        self.shell = os.environ.get("SHELL", "powershell.exe")
    
    def get_system_prompt(self):
        """Get the system prompt from prompt.txt."""
        yolo_path = os.path.abspath(__file__)
        prompt_path = os.path.dirname(yolo_path)
        
        prompt_file = os.path.join(prompt_path, "prompt.txt")
        system_prompt = open(prompt_file, "r").read()
        system_prompt = system_prompt.replace("{shell}", self.shell)
        system_prompt = system_prompt.replace("{os}", self.get_os_friendly_name())
        
        return system_prompt
    
    def get_os_friendly_name(self):
        """Get a friendly name for the OS."""
        os_name = platform.system()
        
        if os_name == "Linux":
            return "Linux/" + distro.name(pretty=True)
        elif os_name == "Windows":
            return os_name
        elif os_name == "Darwin":
            return "Darwin/macOS"
        else:
            return os_name
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Container(id="status-bar"):
            yield Static(f"API: {self.config.get('api', 'unknown')} | Model: {self.config.get('model', 'unknown')}")
        
        with Container(id="prompt-container"):
            yield TextArea(id="prompt-input", placeholder="Enter your prompt here...")
        
        with Container(id="response-container"):
            yield TextArea(id="response-output", placeholder="AI response will appear here...", read_only=True)
        
        with Horizontal(id="button-container"):
            yield Button("Submit", variant="primary", classes="button", id="submit-button")
            yield Button("Execute", variant="success", classes="button", id="execute-button")
            yield Button("Copy", variant="default", classes="button", id="copy-button")
            yield Button("Clear", variant="error", classes="button", id="clear-button")
        
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "submit-button":
            self.action_submit()
        elif button_id == "execute-button":
            self.action_execute()
        elif button_id == "copy-button":
            self.action_copy()
        elif button_id == "clear-button":
            self.action_clear()
    
    def action_submit(self) -> None:
        """Submit the prompt to the AI model."""
        prompt_input = self.query_one("#prompt-input")
        response_output = self.query_one("#response-output")
        
        user_prompt = prompt_input.text
        if not user_prompt:
            response_output.text = "Please enter a prompt first."
            return
        
        system_prompt = self.get_system_prompt()
        
        try:
            response = self.client.chat(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )
            
            response_output.text = response
        except Exception as e:
            response_output.text = f"Error: {str(e)}"
    
    def action_execute(self) -> None:
        """Execute the command from the AI response."""
        response_output = self.query_one("#response-output")
        command = response_output.text
        
        if not command:
            response_output.text = "No command to execute."
            return
        
        try:
            if self.shell == "powershell.exe":
                result = subprocess.run([self.shell, "/c", command], shell=False, capture_output=True, text=True)
            else:
                result = subprocess.run([self.shell, "-c", command], shell=False, capture_output=True, text=True)
            
            output = result.stdout
            if result.stderr:
                output += "\n\nErrors:\n" + result.stderr
            
            response_output.text = f"Command: {command}\n\nOutput:\n{output}"
        except Exception as e:
            response_output.text = f"Error executing command: {str(e)}"
    
    def action_copy(self) -> None:
        """Copy the AI response to clipboard."""
        response_output = self.query_one("#response-output")
        command = response_output.text
        
        if not command:
            return
        
        try:
            pyperclip.copy(command)
            self.notify("Copied to clipboard", title="Success")
        except Exception as e:
            self.notify(f"Error copying to clipboard: {str(e)}", title="Error")
    
    def action_clear(self) -> None:
        """Clear the input and output fields."""
        prompt_input = self.query_one("#prompt-input")
        response_output = self.query_one("#response-output")
        
        prompt_input.text = ""
        response_output.text = ""

def main():
    """Run the Textual app."""
    app = YoloApp()
    app.run()

if __name__ == "__main__":
    main()
