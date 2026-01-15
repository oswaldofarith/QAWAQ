"""
Django management command to analyze database performance.

Shows slow queries, index usage, and table statistics.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Analyze database performance and show statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slow-queries',
            action='store_true',
            help='Show slow queries from pg_stat_statements',
        )
        parser.add_argument(
            '--index-usage',
            action='store_true',
            help='Show index usage statistics',
        )
        parser.add_argument(
            '--table-stats', 
            action='store_true',
            help='Show table size and row count',
        )

    def handle(self, *args, **options):
        if options['slow_queries']:
            self.show_slow_queries()
        
        if options['index_usage']:
            self.show_index_usage()
        
        if options['table_stats']:
            self.show_table_stats()
        
        if not any([options['slow_queries'], options['index_usage'], options['table_stats']]):
            self.stdout.write("Use --slow-queries, --index-usage, or --table-stats")
            self.stdout.write("\nQuick stats:")
            self.show_table_stats()

    def show_slow_queries(self):
        """Show slowest queries from pg_stat_statements."""
        self.stdout.write(self.style.SUCCESS('\n=== Top 10 Slowest Queries ===\n'))
        
        sql = """
        SELECT 
            LEFT(query, 80) as query_preview,
            calls,
            ROUND(total_exec_time::numeric, 2) as total_ms,
            ROUND(mean_exec_time::numeric, 2) as mean_ms,
            ROUND(max_exec_time::numeric, 2) as max_ms
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat_statements%'
        ORDER BY mean_exec_time DESC
        LIMIT 10;
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                if not rows:
                    self.stdout.write("No query statistics available. Enable pg_stat_statements extension.")
                    return
                
                self.stdout.write(f"{'Query':<80} {'Calls':<10} {'Total (ms)':<12} {'Mean (ms)':<10} {'Max (ms)':<10}")
                self.stdout.write("-" * 140)
                
                for row in rows:
                    query, calls, total, mean, max_time = row
                    self.stdout.write(f"{query:<80} {calls:<10} {total:<12} {mean:<10} {max_time:<10}")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            self.stdout.write("\nMake sure pg_stat_statements extension is installed:")
            self.stdout.write("  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")

    def show_index_usage(self):
        """Show index usage statistics."""
        self.stdout.write(self.style.SUCCESS('\n=== Index Usage Statistics ===\n'))
        
        sql = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        LIMIT 20;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            self.stdout.write(f"{'Table':<30} {'Index':<35} {'Scans':<10} {'Tuples Read':<12} {'Size':<10}")
            self.stdout.write("-" * 120)
            
            for row in rows:
                schema, table, index, scans, reads, fetches, size = row
                self.stdout.write(f"{table:<30} {index:<35} {scans:<10} {reads:<12} {size:<10}")
                
            # Show unused indexes
            self.stdout.write(self.style.WARNING('\n--- Potentially Unused Indexes (0 scans) ---\n'))
            
            sql_unused = """
            SELECT 
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) as size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            AND idx_scan = 0
            ORDER BY pg_relation_size(indexrelid) DESC;
            """
            
            cursor.execute(sql_unused)
            unused = cursor.fetchall()
            
            if unused:
                for table, index, size in unused:
                    self.stdout.write(f"  {table}.{index} ({size})")
            else:
                self.stdout.write("  All indexes are being used!")

    def show_table_stats(self):
        """Show table statistics."""
        self.stdout.write(self.style.SUCCESS('\n=== Table Statistics ===\n'))
        
        # QAWAQ main tables
        tables = [
            'monitor_equipo',
            'monitor_medidor',
            'monitor_historial_disponibilidad',
            'monitor_eventofacturacion',
            'monitor_ciclofacturacion',
            'monitor_porcion',
        ]
        
        for table in tables:
            sql = f"""
            SELECT 
                '{table}' as table_name,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                pg_size_pretty(pg_total_relation_size('{table}')) as total_size,
                pg_size_pretty(pg_relation_size('{table}')) as table_size,
                pg_size_pretty(pg_total_relation_size('{table}') - pg_relation_size('{table}')) as indexes_size,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE relname = '{table}';
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
                
                if row:
                    (name, inserts, updates, deletes, live, dead, total_size, 
                     table_size, indexes_size, vacuum, autovacuum, analyze, autoanalyze) = row
                    
                    self.stdout.write(f"\n{name}:")
                    self.stdout.write(f"  Rows: {live:,} live, {dead:,} dead")
                    self.stdout.write(f"  Size: {total_size} (table: {table_size}, indexes: {indexes_size})")
                    self.stdout.write(f"  Operations: {inserts:,} inserts, {updates:,} updates, {deletes:,} deletes")
                    
                    if dead > 1000:
                        self.stdout.write(self.style.WARNING(f"  ⚠ High dead tuple count. Consider VACUUM."))
                    
                    if autoanalyze:
                        self.stdout.write(f"  Last analyze: {autoanalyze}")
