import asyncio
import json
import os
import time

class ScriptController:
    """
    JSON based script controller for YCY Device
    """
    def __init__(self, device):
        self.device = device
        self.is_running = False
        self.task = None

    async def start(self, script_path):
        """
        Start executing a JSON script
        """
        if self.is_running:
            return

        # Load script
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")
            
        with open(script_path, 'r', encoding='utf-8') as f:
            try:
                script_data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in script: {e}")

        actions = script_data.get('actions', [])
        if not actions:
            raise ValueError("No actions defined in the script.")
            
        loop_script = script_data.get('loop', False)

        self.is_running = True
        self.task = asyncio.create_task(self._run_script(actions, loop_script))

    async def stop(self):
        """
        Stop script execution
        """
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        # Stop all channels on exit
        if self.device:
            for channel in ['A', 'B', 'C']:
                await self.device.set_speed(channel, 0)
                await self.device.set_mode(channel, 0)

    async def _run_script(self, actions, loop_script):
        """
        Background task to execute the script loop
        """
        try:
            while self.is_running:
                for action in actions:
                    if not self.is_running:
                        break
                        
                    duration = action.get('duration', 0)
                    if 'A' in action: await self._apply_channel('A', action['A'])
                    if 'B' in action: await self._apply_channel('B', action['B'])
                    if 'C' in action: await self._apply_channel('C', action['C'])
                        
                    if duration > 0:
                        # Sleep in small increments to be responsive to cancellation
                        time_slept = 0
                        while time_slept < duration and self.is_running:
                            await asyncio.sleep(0.1)
                            time_slept += 0.1
                            
                if not loop_script:
                    break
        finally:
            self.is_running = False
            # Clean up by stopping all channels
            if self.device:
                for channel in ['A', 'B', 'C']:
                    await self.device.set_speed(channel, 0)
                    await self.device.set_mode(channel, 0)

    async def _apply_channel(self, channel, instruction):
        """
        Apply settings for a specific channel
        """
        if not isinstance(instruction, dict):
            return

        ctype = instruction.get('type')
        cvalue = instruction.get('value', 0)

        if ctype == 'speed':
            await self.device.set_speed(channel, cvalue)
        elif ctype == 'mode':
            await self.device.set_mode(channel, cvalue)
