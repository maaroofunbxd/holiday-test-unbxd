#!/usr/bin/env python3
"""
Command Workshop - Interactive tool for testing Unix commands and building scripts
Test commands one by one, save what works, build scripts from successful commands
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class CommandWorkshop:
    def __init__(self):
        self.successful_commands = []
        self.failed_commands = []
        self.current_session = []
        
    def print_banner(self):
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════╗")
        print("║     Command Workshop - Test & Build Scripts    ║")
        print("╚════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        print(f"{Colors.GREEN}Workflow:{Colors.RESET}")
        print("  1. Test commands one by one")
        print("  2. See which ones work")
        print("  3. Save successful commands")
        print("  4. Build scripts from what worked")
        print()
        print(f"{Colors.YELLOW}Commands:{Colors.RESET}")
        print("  .help      - Show help")
        print("  .save      - Save successful commands to script")
        print("  .list      - List successful commands")
        print("  .clear     - Clear successful commands")
        print("  .history   - Show command history")
        print("  .exit      - Exit")
        print()
    
    def test_command(self, command):
        """Test a Unix command and return success status"""
        try:
            # Try to execute as shell command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Print output
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(f"{Colors.YELLOW}{result.stderr}{Colors.RESET}", end='', file=sys.stderr)
            
            success = result.returncode == 0
            
            if success:
                print(f"{Colors.GREEN}✓ Success{Colors.RESET}")
                self.successful_commands.append(command)
                self.current_session.append(('success', command))
            else:
                print(f"{Colors.RED}✗ Failed (exit code: {result.returncode}){Colors.RESET}")
                self.failed_commands.append(command)
                self.current_session.append(('failed', command))
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"{Colors.RED}✗ Timeout{Colors.RESET}")
            self.failed_commands.append(command)
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
            self.failed_commands.append(command)
            return False
    
    def list_successful(self):
        """List all successful commands"""
        if not self.successful_commands:
            print(f"{Colors.YELLOW}No successful commands yet{Colors.RESET}")
            return
        
        print(f"{Colors.GREEN}Successful Commands ({len(self.successful_commands)}):{Colors.RESET}")
        for i, cmd in enumerate(self.successful_commands, 1):
            print(f"  {i:2d}. {cmd}")
    
    def save_to_script(self, filename=None):
        """Save successful commands to a script file"""
        if not self.successful_commands:
            print(f"{Colors.YELLOW}No successful commands to save{Colors.RESET}")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workshop_script_{timestamp}.sh"
        
        with open(filename, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"# Generated from Command Workshop\n")
            f.write(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# {len(self.successful_commands)} successful commands\n\n")
            
            for cmd in self.successful_commands:
                f.write(f"{cmd}\n")
        
        os.chmod(filename, 0o755)
        print(f"{Colors.GREEN}Saved {len(self.successful_commands)} commands to: {filename}{Colors.RESET}")
        return filename
    
    def save_to_glue(self, filename=None):
        """Save successful commands to a GlueLang script"""
        if not self.successful_commands:
            print(f"{Colors.YELLOW}No successful commands to save{Colors.RESET}")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workshop_script_{timestamp}.glue"
        
        with open(filename, 'w') as f:
            f.write("import PATH\n\n")
            f.write(f"# Generated from Command Workshop\n")
            f.write(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# {len(self.successful_commands)} successful commands\n\n")
            
            for cmd in self.successful_commands:
                # Try to convert to GlueLang syntax
                # Simple conversion - may need manual adjustment
                glue_cmd = cmd.replace('|', '>>=')
                f.write(f"{glue_cmd}\n")
        
        print(f"{Colors.GREEN}Saved {len(self.successful_commands)} commands to: {filename}{Colors.RESET}")
        print(f"{Colors.YELLOW}Note: May need manual adjustment for GlueLang syntax{Colors.RESET}")
        return filename
    
    def show_history(self):
        """Show command history"""
        if not self.current_session:
            print(f"{Colors.YELLOW}No commands executed yet{Colors.RESET}")
            return
        
        print(f"{Colors.CYAN}Command History:{Colors.RESET}")
        for i, (status, cmd) in enumerate(self.current_session, 1):
            icon = f"{Colors.GREEN}✓{Colors.RESET}" if status == 'success' else f"{Colors.RED}✗{Colors.RESET}"
            print(f"  {i:2d}. {icon} {cmd}")
    
    def clear_successful(self):
        """Clear successful commands list"""
        count = len(self.successful_commands)
        self.successful_commands = []
        print(f"{Colors.YELLOW}Cleared {count} successful commands{Colors.RESET}")
    
    def run(self):
        """Main REPL loop"""
        self.print_banner()
        
        cmd_count = 1
        
        try:
            import readline
            readline.parse_and_bind('tab: complete')
        except ImportError:
            pass
        
        while True:
            try:
                prompt = f"{Colors.GREEN}test[{cmd_count}]> {Colors.RESET}"
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input in ['.exit', '.quit', 'exit', 'quit']:
                    if self.successful_commands:
                        print(f"\n{Colors.YELLOW}You have {len(self.successful_commands)} successful commands.{Colors.RESET}")
                        save = input("Save to script? (y/n): ").strip().lower()
                        if save == 'y':
                            self.save_to_script()
                    print(f"{Colors.BLUE}Goodbye!{Colors.RESET}")
                    break
                
                elif user_input == '.help':
                    self.print_banner()
                    continue
                
                elif user_input == '.list':
                    self.list_successful()
                    continue
                
                elif user_input == '.save':
                    self.save_to_script()
                    continue
                
                elif user_input.startswith('.save '):
                    filename = user_input[6:].strip()
                    self.save_to_script(filename)
                    continue
                
                elif user_input == '.glue':
                    self.save_to_glue()
                    continue
                
                elif user_input.startswith('.glue '):
                    filename = user_input[6:].strip()
                    self.save_to_glue(filename)
                    continue
                
                elif user_input == '.clear':
                    self.clear_successful()
                    continue
                
                elif user_input == '.history':
                    self.show_history()
                    continue
                
                elif user_input.startswith('.'):
                    print(f"{Colors.RED}Unknown command: {user_input}{Colors.RESET}")
                    print("Type .help for available commands")
                    continue
                
                # Test the command
                self.test_command(user_input)
                cmd_count += 1
                
            except EOFError:
                print()
                if self.successful_commands:
                    self.save_to_script()
                print(f"{Colors.BLUE}Goodbye!{Colors.RESET}")
                break
            except KeyboardInterrupt:
                print()
                continue

if __name__ == '__main__':
    workshop = CommandWorkshop()
    workshop.run()
