#!/usr/bin/env python3
"""
🚀 Optimized Raspberry Pi Server Monitor with Dynamic GIFs
Features: Usage-based GIF switching, split-screen layout, rotating info panels
Optimized for lower resource consumption
"""

import time
import psutil
import subprocess
import os
import glob
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

class OptimizedServerMonitor:
    def __init__(self, i2c_port=1, i2c_address=0x3C, gif_directory="./gifs"):
        """Initialize the optimized OLED display system"""
        print("🎮 Initializing Optimized Server Monitor...")
        
        # Initialize I2C and OLED display
        serial = i2c(port=i2c_port, address=i2c_address)
        self.device = ssd1306(serial, width=128, height=64)
        
        # Configuration for performance tuning
        self.update_intervals = {
            'stats': 1.0,      # Update system stats every second
            'gif_frame': 0.1,  # GIF frame update interval
            'page_rotate': 3.0, # Page rotation interval
            'network': 1.0,    # Network stats update interval
        }
        
        # GIF Animation System - Dynamic based on usage
        self.gif_directory = gif_directory
        self.gif_sets = {
            'low': [],
            'medium': [],
            'high': []
        }
        self.current_usage_level = 'low'
        self.current_frame = 0
        self.last_frame_time = 0
        
        # Information rotation system
        self.info_pages = ['system', 'storage', 'network', 'processes']
        self.current_info_page = 0
        self.page_change_time = time.time()
        
        # Network speed tracking
        self.prev_net_io = psutil.net_io_counters()
        self.prev_net_time = time.time()
        self.net_up_speed = 0.0
        self.net_down_speed = 0.0
        
        # Cached values to avoid redundant calculations
        self.cached_stats = None
        self.last_stats_update = 0
        
        # Load fonts
        self.load_fonts()
        
        # Load all GIF sets
        self.load_all_gifs()
        
        print("✅ Optimized Monitor initialized successfully!")

    def load_fonts(self):
        """Load the best available fonts"""
        try:
            # Pre-load and cache font objects
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
            self.small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
            self.tiny_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 6)
            self.notification_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
        except:
            # Fallback to default font
            self.font = ImageFont.load_default()
            self.small_font = self.font
            self.tiny_font = self.font
            self.notification_font = self.font

    def load_all_gifs(self):
        """Load GIFs for all usage levels with optimization"""
        usage_levels = ['low', 'medium', 'high']
        
        for level in usage_levels:
            gif_path = os.path.join(self.gif_directory, f"{level}.gif")
            if os.path.exists(gif_path):
                print(f"🎬 Loading {level}.gif...")
                self.gif_sets[level] = self.load_gif_frames(gif_path)
            else:
                print(f"📂 Creating default {level} animation...")
                self.gif_sets[level] = self.create_default_animation(level)
        
        print(f"✨ Loaded GIFs: Low({len(self.gif_sets['low'])}), Medium({len(self.gif_sets['medium'])}), High({len(self.gif_sets['high'])})")

    def load_gif_frames(self, gif_path):
        """Optimized GIF loading with pre-processing"""
        frames = []
        
        try:
            with Image.open(gif_path) as gif:
                # Get frame duration first
                frame_duration = gif.info.get('duration', 100) / 1000.0
                self.update_intervals['gif_frame'] = frame_duration
                
                # Process all frames
                for frame_num in range(gif.n_frames):
                    try:
                        gif.seek(frame_num)
                        frame = gif.copy()
                        
                        # Resize and convert to monochrome
                        frame = frame.resize((64, 48), Image.Resampling.LANCZOS)
                        frame = frame.convert('L')
                        frame = frame.point(lambda x: 255 if x > 128 else 0, mode='1')
                        
                        frames.append(frame)
                    except EOFError:
                        break
                
        except Exception as e:
            print(f"❌ Error loading {gif_path}: {e}")
            frames = self.create_error_animation()
        
        return frames

    def create_default_animation(self, level):
        """Create simple default animation with minimal resources"""
        frames = []
        pattern = {
            'low': [1, 0, 0, 0],
            'medium': [1, 0, 1, 0],
            'high': [1, 1, 0, 0]
        }
        
        # Create just 4 frames for default animation
        for i in range(4):
            frame = Image.new('1', (64, 48), 0)
            draw = ImageDraw.Draw(frame)
            
            if pattern[level][i]:
                draw.rectangle([20, 10, 44, 34], fill=1)
            
            draw.text((15, 36), level.upper()[:4], font=self.small_font, fill=1)
            frames.append(frame)
        
        return frames

    def create_error_animation(self):
        """Simple error display"""
        frame = Image.new('1', (64, 48), 0)
        draw = ImageDraw.Draw(frame)
        draw.text((10, 18), "ERR", font=self.small_font, fill=1)
        return [frame]

    def get_system_stats(self):
        """Get system statistics with caching to reduce CPU load"""
        current_time = time.time()
        
        # Return cached stats if not expired
        if (self.cached_stats and 
            current_time - self.last_stats_update < self.update_intervals['stats']):
            return self.cached_stats
        
        stats = {}
        
        # CPU stats
        stats['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        
        # Memory stats
        memory = psutil.virtual_memory()
        stats['memory_percent'] = memory.percent
        stats['memory_used_gb'] = memory.used / (1024**3)
        stats['memory_total_gb'] = memory.total / (1024**3)
        
        # Disk stats (cache these as they change slowly)
        if not hasattr(self, 'disk_total_gb') or current_time - self.last_stats_update > 30:
            disk = psutil.disk_usage('/')
            self.disk_total_gb = disk.total / (1024**3)
            self.disk_free_gb = disk.free / (1024**3)
            self.disk_percent = (disk.used / disk.total) * 100
        
        stats['disk_percent'] = self.disk_percent
        stats['disk_free_gb'] = self.disk_free_gb
        stats['disk_total_gb'] = self.disk_total_gb
        
        # Temperature (Raspberry Pi) - read less frequently
        if not hasattr(self, 'cpu_temp') or current_time - self.last_stats_update > 5:
            try:
                temp_output = subprocess.check_output(['vcgencmd', 'measure_temp'], timeout=1).decode()
                self.cpu_temp = float(temp_output.split('=')[1].split('°')[0])
            except:
                self.cpu_temp = 0
        
        stats['cpu_temp'] = self.cpu_temp
        
        # Network speed calculation
        self.update_network_speeds()
        stats['net_up_speed'] = self.net_up_speed
        stats['net_down_speed'] = self.net_down_speed
        
        # System load
        try:
            stats['load_avg'] = os.getloadavg()[0]
        except:
            stats['load_avg'] = 0
        
        # Process count (cache this as it changes slowly)
        if not hasattr(self, 'process_count') or current_time - self.last_stats_update > 10:
            self.process_count = len(psutil.pids())
        
        stats['process_count'] = self.process_count
        
        # Top processes (only update when needed)
        if self.info_pages[self.current_info_page] == 'processes':
            stats['top_processes'] = self.get_top_processes()
        else:
            stats['top_processes'] = []
        
        # Cache the results
        self.cached_stats = stats
        self.last_stats_update = current_time
        
        return stats

    def get_top_processes(self):
        """Get top 3 processes by CPU usage - optimized with timeout"""
        processes = []
        try:
            # Use a short timeout to prevent hanging
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 0:
                        processes.append(proc.info)
                        # Limit to 10 processes for sorting to save resources
                        if len(processes) >= 10:
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage and return top 3
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:3]
        except:
            return []

    def update_network_speeds(self):
        """Calculate real-time network speeds with interval checking"""
        current_time = time.time()
        
        if current_time - self.prev_net_time >= self.update_intervals['network']:
            current_net = psutil.net_io_counters()
            time_diff = current_time - self.prev_net_time
            
            bytes_sent_diff = current_net.bytes_sent - self.prev_net_io.bytes_sent
            bytes_recv_diff = current_net.bytes_recv - self.prev_net_io.bytes_recv
            
            self.net_up_speed = (bytes_sent_diff / time_diff) / 1024  # KB/s
            self.net_down_speed = (bytes_recv_diff / time_diff) / 1024  # KB/s
            
            self.prev_net_io = current_net
            self.prev_net_time = current_time

    def determine_usage_level(self, stats):
        """Determine current system usage level with hysteresis to prevent flickering"""
        cpu_score = min(stats['cpu_percent'] / 100.0, 1.0)
        ram_score = min(stats['memory_percent'] / 100.0, 1.0)
        net_score = min((stats['net_up_speed'] + stats['net_down_speed']) / 1000.0, 1.0)
        
        avg_usage = (cpu_score + ram_score + net_score) / 3.0
        
        # Add hysteresis to prevent rapid switching
        if avg_usage >= 0.7 or (self.current_usage_level == 'high' and avg_usage >= 0.5):
            return 'high'
        elif avg_usage >= 0.4 or (self.current_usage_level == 'medium' and avg_usage >= 0.3):
            return 'medium'
        else:
            return 'low'

    def format_speed(self, speed_kb):
        """Format network speed for display"""
        if speed_kb >= 1024:
            return f"{speed_kb/1024:.1f}M"
        elif speed_kb >= 10:
            return f"{speed_kb:.0f}K"
        else:
            return f"{speed_kb:.1f}K"

    def draw_notification_bar(self, draw, stats):
        """Draw notification bar with CPU, RAM, Network"""
        # Background
        draw.rectangle([(0, 0), (127, 14)], fill=1, outline=1)
        
        # CPU Section
        cpu_text = f"CPU {stats['cpu_percent']:4.1f}%"
        draw.text((2, 2), cpu_text, font=self.notification_font, fill=0)
        
        # RAM Section
        ram_text = f"RAM {stats['memory_percent']:4.1f}%"
        draw.text((44, 2), ram_text, font=self.notification_font, fill=0)
        
        # Network Section
        net_text = f"NET {self.format_speed(stats['net_up_speed'] + stats['net_down_speed'])}"
        bbox = draw.textbbox((0, 0), net_text, font=self.notification_font)
        text_width = bbox[2] - bbox[0]
        draw.text((126 - text_width, 2), net_text, font=self.notification_font, fill=0)
        
        # Separators
        draw.line([(42, 1), (42, 13)], fill=0, width=1)
        draw.line([(85, 1), (85, 13)], fill=0, width=1)

    def draw_dynamic_gif(self, draw, stats):
        """Draw the appropriate GIF based on current usage level"""
        # Update usage level with less frequent checks
        current_time = time.time()
        if current_time - self.last_stats_update >= self.update_intervals['stats']:
            new_level = self.determine_usage_level(stats)
            if new_level != self.current_usage_level:
                self.current_usage_level = new_level
                self.current_frame = 0
        
        # Get current GIF set
        current_gif_set = self.gif_sets[self.current_usage_level]
        
        if not current_gif_set:
            return
        
        # Update frame timing
        if current_time - self.last_frame_time >= self.update_intervals['gif_frame']:
            self.current_frame = (self.current_frame + 1) % len(current_gif_set)
            self.last_frame_time = current_time
        
        # Draw current frame on left side
        frame = current_gif_set[self.current_frame]
        for y in range(48):
            for x in range(64):
                if frame.getpixel((x, y)):
                    draw.point((x, y + 15), fill=1)

    def draw_info_panel(self, draw, stats):
        """Draw rotating information panel on right side"""
        # Check if it's time to rotate pages
        current_time = time.time()
        if current_time - self.page_change_time >= self.update_intervals['page_rotate']:
            self.current_info_page = (self.current_info_page + 1) % len(self.info_pages)
            self.page_change_time = current_time
        
        # Draw border for info panel
        draw.line([(64, 15), (64, 63)], fill=1, width=1)
        
        # Draw current info page
        if self.info_pages[self.current_info_page] == 'system':
            self.draw_system_info(draw, stats)
        elif self.info_pages[self.current_info_page] == 'storage':
            self.draw_storage_info(draw, stats)
        elif self.info_pages[self.current_info_page] == 'network':
            self.draw_network_info(draw, stats)
        elif self.info_pages[self.current_info_page] == 'processes':
            self.draw_processes_info(draw, stats)
        
        # Page indicator at bottom right
        page_text = f"{self.current_info_page + 1}/{len(self.info_pages)}"
        draw.text((115, 55), page_text, font=self.tiny_font, fill=1)

    def draw_system_info(self, draw, stats):
        """Draw system information"""
        y = 18
        
        draw.text((66, y), "SYS", font=self.small_font, fill=1)
        y += 10
        
        draw.text((66, y), f"T:{stats['cpu_temp']:2.0f}°C", font=self.tiny_font, fill=1)
        y += 8
        
        draw.text((66, y), f"L:{stats['load_avg']:4.2f}", font=self.tiny_font, fill=1)
        y += 8
        
        draw.text((66, y), f"P:{stats['process_count']}", font=self.tiny_font, fill=1)

    def draw_storage_info(self, draw, stats):
        """Draw storage information"""
        y = 18
        
        draw.text((66, y), "DISK", font=self.small_font, fill=1)
        y += 10
        
        draw.text((66, y), f"U:{stats['disk_percent']:2.0f}%", font=self.tiny_font, fill=1)
        y += 8
        
        # Progress bar for disk usage
        bar_width = int((stats['disk_percent'] / 100) * 40)
        draw.rectangle([(66, y), (66 + bar_width, y + 4)], fill=1)
        draw.rectangle([(66, y), (106, y + 4)], outline=1)
        y += 8
        
        draw.text((66, y), f"F:{stats['disk_free_gb']:2.1f}G", font=self.tiny_font, fill=1)

    def draw_network_info(self, draw, stats):
        """Draw network information"""
        y = 18
        
        draw.text((66, y), "NET", font=self.small_font, fill=1)
        y += 10
        
        draw.text((66, y), f"U:{self.format_speed(stats['net_up_speed'])}", font=self.tiny_font, fill=1)
        y += 8
        
        draw.text((66, y), f"D:{self.format_speed(stats['net_down_speed'])}", font=self.tiny_font, fill=1)

    def draw_processes_info(self, draw, stats):
        """Draw top processes information"""
        y = 18
        
        draw.text((66, y), "PROC", font=self.small_font, fill=1)
        y += 10
        
        for i, proc in enumerate(stats['top_processes'][:3]):
            name = proc['name'][:7]  # Truncate name
            cpu = proc['cpu_percent']
            draw.text((66, y), f"{name}:{cpu:.0f}%", font=self.tiny_font, fill=1)
            y += 8

    def update_display(self):
        """Update the entire display with optimized redraws"""
        with canvas(self.device) as draw:
            # Get system stats (with caching)
            stats = self.get_system_stats()
            
            # Draw notification bar
            self.draw_notification_bar(draw, stats)
            
            # Draw dynamic GIF
            self.draw_dynamic_gif(draw, stats)
            
            # Draw info panel
            self.draw_info_panel(draw, stats)

    def run(self):
        """🚀 Run the optimized monitor!"""
        print("\n" + "="*60)
        print("🎮 OPTIMIZED RASPBERRY PI SERVER MONITOR")
        print(f"📂 GIF Directory: {os.path.abspath(self.gif_directory)}")
        print("⚡ Optimized for lower resource usage")
        print("🔥 Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        try:
            update_counter = 0
            last_status_time = time.time()
            
            while True:
                self.update_display()
                update_counter += 1
                
                # Print status every 10 seconds instead of every 100 updates
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    stats = self.get_system_stats()
                    print(f"📊 Usage: {self.current_usage_level.upper()} | "
                          f"CPU: {stats['cpu_percent']:5.1f}% | "
                          f"RAM: {stats['memory_percent']:5.1f}% | "
                          f"Page: {self.info_pages[self.current_info_page].upper()}")
                    last_status_time = current_time
                
                # Adjust sleep time based on needs
                time.sleep(0.1)  # Reduced from 0.05 to 0.1 for lower CPU
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Optimized Server Monitor...")
            
            # Simple goodbye message
            with canvas(self.device) as draw:
                draw.rectangle([(0, 0), (127, 63)], fill=0)
                draw.text((35, 27), "BYE!", font=self.font, fill=1)
            
            time.sleep(1)
            self.device.cleanup()
            print("✅ Optimized Monitor stopped successfully!")

def main():
    """Main function to start the optimized monitor"""
    # Create gifs directory if needed
    gif_dir = "./gifs"
    if not os.path.exists(gif_dir):
        os.makedirs(gif_dir)
        print(f"📁 Created directory: {gif_dir}")
    
    # Check for required GIF files
    required_gifs = ['low.gif', 'medium.gif', 'high.gif']
    missing_gifs = []
    
    for gif_name in required_gifs:
        if not os.path.exists(os.path.join(gif_dir, gif_name)):
            missing_gifs.append(gif_name)
    
    if missing_gifs:
        print(f"🎬 Missing GIF files: {', '.join(missing_gifs)}")
        print("💡 Default animations will be used")
    
    # Start the optimized monitor
    monitor = OptimizedServerMonitor(gif_directory=gif_dir)
    monitor.run()

if __name__ == "__main__":
    main()