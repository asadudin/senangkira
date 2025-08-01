"""
Django Management Command: Validate Performance Optimizations

Usage:
    python manage.py validate_performance
    python manage.py validate_performance --detailed
    python manage.py validate_performance --output report.json
    python manage.py validate_performance --quick
"""

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from dashboard.benchmark_validation import PerformanceBenchmark


class Command(BaseCommand):
    help = 'Validate SK-602 performance optimizations with comprehensive benchmarking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Run detailed benchmarks with more iterations',
        )
        
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run quick benchmarks with fewer iterations',
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Save detailed report to specified JSON file',
        )
        
        parser.add_argument(
            '--concurrent-users',
            type=int,
            default=8,
            help='Number of concurrent users for load testing (default: 8)',
        )
        
        parser.add_argument(
            '--refresh-iterations',
            type=int,
            help='Number of iterations for dashboard refresh test (default: auto)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting SK-602 Performance Validation...\n')
        )
        
        # Determine test parameters
        if options['detailed']:
            refresh_iterations = options['refresh_iterations'] or 20
            api_iterations = 10
            concurrent_users = options['concurrent_users']
            concurrent_requests = 5
            db_iterations = 30
            
            self.stdout.write("Running DETAILED benchmark suite...")
            
        elif options['quick']:
            refresh_iterations = options['refresh_iterations'] or 5
            api_iterations = 3
            concurrent_users = 4
            concurrent_requests = 2
            db_iterations = 10
            
            self.stdout.write("Running QUICK benchmark suite...")
            
        else:
            refresh_iterations = options['refresh_iterations'] or 10
            api_iterations = 5
            concurrent_users = options['concurrent_users']
            concurrent_requests = 3
            db_iterations = 15
            
            self.stdout.write("Running STANDARD benchmark suite...")
        
        # Run benchmark
        benchmark = PerformanceBenchmark()
        
        try:
            self.stdout.write("Setting up test environment...")
            benchmark.setup()
            
            # Run individual benchmarks with progress updates
            self.stdout.write("\n1/4 Testing dashboard refresh performance...")
            refresh_results = benchmark.benchmark_dashboard_refresh(iterations=refresh_iterations)
            
            self.stdout.write("2/4 Testing API endpoint performance...")
            api_results = benchmark.benchmark_api_endpoints(iterations=api_iterations)
            
            self.stdout.write("3/4 Testing concurrent request handling...")
            concurrent_results = benchmark.benchmark_concurrent_requests(
                concurrent_users=concurrent_users,
                requests_per_user=concurrent_requests
            )
            
            self.stdout.write("4/4 Testing database query performance...")
            db_results = benchmark.benchmark_database_queries(iterations=db_iterations)
            
            # Generate report
            self.stdout.write("\nGenerating performance report...")
            report = benchmark.generate_performance_report(0)  # Time not needed for manual run
            
            # Display results
            self._display_results(report)
            
            # Save detailed report if requested
            if options['output']:
                self._save_report(report, options['output'])
            
            # Determine overall success
            dashboard_target_met = False
            if 'dashboard_refresh' in report.get('critical_metrics', {}):
                dashboard_target_met = report['critical_metrics']['dashboard_refresh'].get('target_achieved', False)
            
            if dashboard_target_met:
                self.stdout.write(
                    self.style.SUCCESS('\n✅ VALIDATION SUCCESSFUL: Performance targets achieved!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\n⚠️  VALIDATION PARTIAL: Some targets not fully achieved')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ VALIDATION FAILED: {str(e)}')
            )
            raise CommandError(f'Benchmark failed: {e}')
            
        finally:
            benchmark.cleanup()
    
    def _display_results(self, report):
        """Display formatted benchmark results."""
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SK-602 PERFORMANCE OPTIMIZATION VALIDATION RESULTS'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        # Critical metrics
        if 'critical_metrics' in report and 'dashboard_refresh' in report['critical_metrics']:
            metrics = report['critical_metrics']['dashboard_refresh']
            
            self.stdout.write(self.style.WARNING('\n🎯 CRITICAL OPTIMIZATION TARGET (Dashboard Refresh):'))
            self.stdout.write(f"   Baseline (from benchmarking): {metrics.get('baseline_time_ms', 1028)}ms")
            self.stdout.write(f"   Original Implementation: {metrics['original_time_ms']}ms")
            self.stdout.write(f"   Optimized Implementation: {metrics['optimized_time_ms']}ms")
            self.stdout.write(f"   Performance Improvement: {metrics['improvement_percentage']:.1f}%")
            self.stdout.write(f"   Target (<500ms): {'✅ ACHIEVED' if metrics['target_achieved'] else '❌ NOT MET'}")
            
            if metrics['target_achieved']:
                time_under_target = 500 - metrics['optimized_time_ms']
                self.stdout.write(f"   Performance Margin: {time_under_target:.1f}ms under target")
        
        # Overall improvements
        if 'performance_improvements' in report:
            self.stdout.write(self.style.WARNING('\n📊 PERFORMANCE IMPROVEMENTS BY OPERATION:'))
            
            for operation, improvement in report['performance_improvements'].items():
                if improvement['time_improvement_percentage'] > 0:
                    status_icon = '🚀' if improvement['time_improvement_percentage'] > 50 else '📈'
                    self.stdout.write(
                        f"   {status_icon} {operation}: "
                        f"{improvement['time_improvement_percentage']:.1f}% faster "
                        f"({improvement['original_avg_time_ms']:.1f}ms → {improvement['optimized_avg_time_ms']:.1f}ms)"
                    )
                    
                    if improvement['cache_hit_rate_improvement'] > 0:
                        self.stdout.write(f"      Cache hit rate improved by {improvement['cache_hit_rate_improvement']:.1f}%")
        
        # Recommendations
        if 'recommendations' in report:
            self.stdout.write(self.style.WARNING('\n💡 OPTIMIZATION ANALYSIS:'))
            for rec in report['recommendations']:
                self.stdout.write(f"   {rec}")
        
        # Summary stats
        if 'benchmark_summary' in report:
            summary = report['benchmark_summary']
            self.stdout.write(self.style.WARNING('\n📋 BENCHMARK SUMMARY:'))
            self.stdout.write(f"   Operations Tested: {summary['total_operations_tested']}")
            self.stdout.write(f"   Total Test Cases: {summary['total_test_cases']}")
            self.stdout.write(f"   Execution Time: {summary.get('total_benchmark_time_seconds', 'N/A')} seconds")
        
        # Optimization techniques
        if 'optimization_summary' in report:
            opt_summary = report['optimization_summary']
            self.stdout.write(self.style.WARNING('\n🔧 OPTIMIZATION TECHNIQUES IMPLEMENTED:'))
            for technique in opt_summary.get('optimization_techniques', []):
                self.stdout.write(f"   ✓ {technique}")
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
    
    def _save_report(self, report, filename):
        """Save detailed report to JSON file."""
        try:
            # Add timestamp to report
            report['generated_at'] = timezone.now().isoformat()
            report['command_info'] = {
                'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
                'python_version': f"{getattr(settings, 'PYTHON_VERSION', 'unknown')}",
                'validation_version': 'SK-602'
            }
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.stdout.write(
                self.style.SUCCESS(f'\n📄 Detailed report saved to: {os.path.abspath(filename)}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to save report: {e}')
            )
    
    def _format_duration(self, seconds):
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"