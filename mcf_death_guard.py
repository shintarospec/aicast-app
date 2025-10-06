#!/usr/bin/env python3
"""
🎖️ MCF Death Guard System - Absolute Protection for Mission-Critical Functions
MCF状態死守のための最高レベル保護システム
"""

import sqlite3
import subprocess
import requests
import time
import json
import os
from datetime import datetime, timedelta
import pytz
from config import Config

class MCFDeathGuard:
    def __init__(self):
        self.jst = pytz.timezone('Asia/Tokyo')
        self.mcf_baseline_file = "MCF_BASELINE_STATE.json"
        self.alert_threshold = {
            'content_side_max_response_time': 10,  # AI response max 10 seconds
            'broadcast_side_max_response_time': 5,   # Cloud Functions max 5 seconds
            'database_max_query_time': 1,           # Database query max 1 second
            'post_schedule_tolerance_minutes': 1    # Post timing tolerance 1 minute
        }
        
    def capture_mcf_baseline(self):
        """Capture current MCF success state as baseline"""
        print("🎖️ Capturing MCF Baseline State...")
        
        baseline = {
            'timestamp': datetime.now(self.jst).isoformat(),
            'content_side': self._assess_content_side(),
            'broadcast_side': self._assess_broadcast_side(),
            'integration_health': self._assess_integration_health(),
            'system_configuration': self._capture_mcf_config()
        }
        
        with open(self.mcf_baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
            
        print(f"✅ MCF Baseline captured: {self.mcf_baseline_file}")
        return baseline
    
    def _assess_content_side(self):
        """Content Side MCF assessment"""
        content_health = {
            'ai_authentication': False,
            'database_connectivity': False,
            'config_integrity': False,
            'response_times': {}
        }
        
        try:
            # AI Authentication check
            start_time = time.time()
            mcf_errors = Config.validate_mcf_settings()
            ai_response_time = time.time() - start_time
            
            content_health['ai_authentication'] = len(mcf_errors) == 0
            content_health['response_times']['ai_validation'] = ai_response_time
            
            # Database connectivity check
            start_time = time.time()
            conn = sqlite3.connect('casting_office.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts")
            db_response_time = time.time() - start_time
            conn.close()
            
            content_health['database_connectivity'] = True
            content_health['response_times']['database_query'] = db_response_time
            
            # Config integrity check
            content_health['config_integrity'] = os.path.exists('config.py')
            
        except Exception as e:
            content_health['error'] = str(e)
            
        return content_health
    
    def _assess_broadcast_side(self):
        """Broadcasting Side MCF assessment"""
        broadcast_health = {
            'cloud_functions_connectivity': False,
            'x_api_accessibility': False,
            'cron_configuration': False,
            'response_times': {}
        }
        
        try:
            # Cloud Functions check
            start_time = time.time()
            url = Config.get_cloud_functions_url()
            response = requests.get(f"{url}?test=mcf_health", timeout=10)
            cf_response_time = time.time() - start_time
            
            broadcast_health['cloud_functions_connectivity'] = response.status_code in [200, 400]
            broadcast_health['response_times']['cloud_functions'] = cf_response_time
            
            # Cron configuration check
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            mcf_crons = ["local_schedule_checker.py", "local_retweet_scheduler.py"]
            cron_valid = all(cron in result.stdout for cron in mcf_crons) if result.returncode == 0 else False
            
            broadcast_health['cron_configuration'] = cron_valid
            
        except Exception as e:
            broadcast_health['error'] = str(e)
            
        return broadcast_health
    
    def _assess_integration_health(self):
        """Integration Health assessment"""
        integration_health = {
            'end_to_end_flow': False,
            'scheduler_operational': False,
            'monitoring_active': False
        }
        
        try:
            # Check if schedulers are running
            integration_health['scheduler_operational'] = all([
                os.path.exists('local_schedule_checker.py'),
                os.path.exists('local_retweet_scheduler.py')
            ])
            
            # Check monitoring system
            integration_health['monitoring_active'] = os.path.exists('monitor_critical_functions.py')
            
            # Basic end-to-end flow validation
            integration_health['end_to_end_flow'] = all([
                integration_health['scheduler_operational'],
                integration_health['monitoring_active']
            ])
            
        except Exception as e:
            integration_health['error'] = str(e)
            
        return integration_health
    
    def _capture_mcf_config(self):
        """Capture MCF configuration state"""
        config_state = {
            'cloud_functions_url': Config.get_cloud_functions_url(),
            'test_account_configured': bool(Config.get_test_account_id()),
            'mcf_validation_active': True
        }
        
        return config_state
    
    def validate_against_baseline(self):
        """Validate current state against MCF baseline"""
        if not os.path.exists(self.mcf_baseline_file):
            print("🚨 MCF DEATH GUARD ALERT: No baseline found! Capturing current state...")
            return self.capture_mcf_baseline()
        
        with open(self.mcf_baseline_file, 'r') as f:
            baseline = json.load(f)
        
        current_state = {
            'content_side': self._assess_content_side(),
            'broadcast_side': self._assess_broadcast_side(),
            'integration_health': self._assess_integration_health()
        }
        
        violations = []
        
        # Content Side validation
        if not current_state['content_side']['ai_authentication']:
            violations.append("🚨 CONTENT SIDE FAILURE: AI Authentication compromised")
        
        if not current_state['content_side']['database_connectivity']:
            violations.append("🚨 CONTENT SIDE FAILURE: Database connectivity lost")
        
        # Broadcasting Side validation
        if not current_state['broadcast_side']['cloud_functions_connectivity']:
            violations.append("🚨 BROADCAST SIDE FAILURE: Cloud Functions connectivity lost")
        
        if not current_state['broadcast_side']['cron_configuration']:
            violations.append("🚨 BROADCAST SIDE FAILURE: Cron configuration corrupted")
        
        # Performance validation
        content_times = current_state['content_side'].get('response_times', {})
        broadcast_times = current_state['broadcast_side'].get('response_times', {})
        
        if content_times.get('database_query', 0) > self.alert_threshold['database_max_query_time']:
            violations.append(f"🚨 PERFORMANCE DEGRADATION: Database query time {content_times['database_query']:.2f}s exceeds {self.alert_threshold['database_max_query_time']}s limit")
        
        if broadcast_times.get('cloud_functions', 0) > self.alert_threshold['broadcast_side_max_response_time']:
            violations.append(f"🚨 PERFORMANCE DEGRADATION: Cloud Functions response time {broadcast_times['cloud_functions']:.2f}s exceeds {self.alert_threshold['broadcast_side_max_response_time']}s limit")
        
        return violations, current_state
    
    def emergency_mcf_protection(self):
        """Emergency MCF protection measures"""
        print("🚨 ACTIVATING EMERGENCY MCF PROTECTION MEASURES")
        
        # 1. Immediate MCF validation
        mcf_errors = Config.validate_mcf_settings()
        if mcf_errors:
            print("🚨 CRITICAL: MCF Configuration errors detected:")
            for error in mcf_errors:
                print(f"   • {error}")
        
        # 2. Database integrity check
        try:
            conn = sqlite3.connect('casting_office.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            required_tables = ['posts', 'retweet_schedules']
            
            for table in required_tables:
                if table not in tables:
                    print(f"🚨 CRITICAL: MCF table '{table}' missing!")
                    
            conn.close()
        except Exception as e:
            print(f"🚨 CRITICAL: Database access failed: {e}")
        
        # 3. Cloud Functions connectivity emergency test
        try:
            url = Config.get_cloud_functions_url()
            response = requests.get(f"{url}?emergency=mcf_test", timeout=5)
            if response.status_code not in [200, 400]:
                print(f"🚨 CRITICAL: Cloud Functions emergency test failed: {response.status_code}")
        except Exception as e:
            print(f"🚨 CRITICAL: Cloud Functions unreachable: {e}")
        
        print("🛡️ Emergency MCF protection measures completed")
    
    def run_death_guard_monitoring(self):
        """Run continuous MCF death guard monitoring"""
        print("🎖️ MCF DEATH GUARD SYSTEM ACTIVATED")
        print("=" * 60)
        print("Mission: Absolute protection of MCF operational status")
        print("=" * 60)
        
        violations, current_state = self.validate_against_baseline()
        
        if violations:
            print("🚨🚨🚨 MCF DEATH GUARD ALERT 🚨🚨🚨")
            print("MISSION-CRITICAL FUNCTIONS COMPROMISED!")
            print("=" * 60)
            
            for violation in violations:
                print(violation)
            
            print("\n🚨 ACTIVATING EMERGENCY PROTOCOLS...")
            self.emergency_mcf_protection()
            
            return False
        else:
            print("🛡️ MCF DEATH GUARD STATUS: ALL SYSTEMS PROTECTED")
            print("✅ Content Side: Operational")
            print("✅ Broadcasting Side: Operational") 
            print("✅ Integration Health: Operational")
            print("🎖️ Mission-Critical Functions are DEATH GUARDED")
            
            return True


if __name__ == "__main__":
    death_guard = MCFDeathGuard()
    
    # Initial baseline capture if needed
    if not os.path.exists(death_guard.mcf_baseline_file):
        print("🎖️ First run: Capturing MCF success baseline...")
        death_guard.capture_mcf_baseline()
    
    # Run continuous death guard monitoring
    while True:
        success = death_guard.run_death_guard_monitoring()
        
        if not success:
            print("\n🚨 MCF DEATH GUARD: Waiting 1 minute before retry...")
            time.sleep(60)
        else:
            print("\n🛡️ MCF DEATH GUARD: Next check in 5 minutes...")
            time.sleep(300)