#!/usr/bin/env python3
"""
Test Runner for Hybrid GNN Fraud Intelligence System
Runs all test suites and generates a summary report
"""

import os
import sys
import subprocess
from pathlib import Path


class TestRunner:
    """Manages test execution and reporting"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {}
        self.total_passed = 0
        self.total_failed = 0
    
    def run_test_file(self, test_file):
        """Run a single test file"""
        print(f"\n{'='*60}")
        print(f"Running: {test_file.name}")
        print('='*60)
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(result.stdout)
                self.results[test_file.name] = "✓ PASSED"
                self.total_passed += 1
            else:
                print(result.stdout)
                print(result.stderr)
                self.results[test_file.name] = "✗ FAILED"
                self.total_failed += 1
                
        except subprocess.TimeoutExpired:
            print(f"✗ Test timeout (30s)")
            self.results[test_file.name] = "✗ TIMEOUT"
            self.total_failed += 1
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.results[test_file.name] = "✗ ERROR"
            self.total_failed += 1
    
    def run_all_tests(self):
        """Run all test files"""
        test_files = [
            self.test_dir / 'test_file_upload.py',
            self.test_dir / 'test_integration_upload_models.py',
            self.test_dir / 'test_config_autodetect.py',
            self.test_dir / 'test_react_error_handling.py',
            self.test_dir / 'test_edge_weights.py',
        ]
        
        print("\n" + "="*60)
        print("HYBRID GNN FRAUD INTELLIGENCE - TEST SUITE")
        print("="*60)
        
        for test_file in test_files:
            if test_file.exists():
                self.run_test_file(test_file)
            else:
                print(f"\n⚠ Test file not found: {test_file.name}")
                self.results[test_file.name] = "⚠ NOT FOUND"
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, result in self.results.items():
            print(f"{test_name:<40} {result}")
        
        print("-"*60)
        print(f"Total Passed: {self.total_passed}")
        print(f"Total Failed: {self.total_failed}")
        
        if self.total_failed == 0:
            print("\n✓ All tests passed!")
        else:
            print(f"\n✗ {self.total_failed} test(s) failed")
        
        print("="*60 + "\n")


def run_single_test(test_name):
    """Run a single test by name"""
    test_file = Path(__file__).parent / f"{test_name}.py"
    
    if not test_file.exists():
        print(f"✗ Test file not found: {test_file}")
        sys.exit(1)
    
    print(f"Running: {test_name}\n")
    subprocess.run([sys.executable, str(test_file)])


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Run specific test
        run_single_test(sys.argv[1])
    else:
        # Run all tests
        runner = TestRunner()
        runner.run_all_tests()
        runner.print_summary()


if __name__ == "__main__":
    main()
