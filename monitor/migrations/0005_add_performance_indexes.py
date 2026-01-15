"""
Custom migration to add database indexes for performance optimization.

This migration adds indexes to frequently queried fields that don't already have them.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0010_medidor_colector'),
    ]

    operations = [
        # Equipo model indexes
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['is_online'], name='monitor_equ_is_onli_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['estado'], name='monitor_equ_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['medio_comunicacion'], name='monitor_equ_medio_c_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['last_seen'], name='monitor_equ_last_se_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['is_online', 'last_seen'], name='monitor_equ_online_time_idx'),
        ),
        
        # Medidor model indexes
        migrations.AddIndex(
            model_name='medidor',
            index=models.Index(fields=['id_medidor'], name='monitor_med_id_medi_idx'),
        ),
        migrations.AddIndex(
            model_name='medidor',
            index=models.Index(fields=['marca'], name='monitor_med_marca_idx'),
        ),
        migrations.AddIndex(
            model_name='medidor',
            index=models.Index(fields=['porcion'], name='monitor_med_porcion_idx'),
        ),
        
        # EventoFacturacion model indexes
        migrations.AddIndex(
            model_name='eventofacturacion',
            index=models.Index(fields=['fecha'], name='monitor_evt_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='eventofacturacion',
            index=models.Index(fields=['tipo_evento'], name='monitor_evt_tipo_ev_idx'),
        ),
        migrations.AddIndex(
            model_name='eventofacturacion',
            index=models.Index(fields=['fecha', 'tipo_evento'], name='monitor_evt_fecha_tipo_idx'),
        ),
        migrations.AddIndex(
            model_name='eventofacturacion',
            index=models.Index(fields=['ciclo', 'porcion'], name='monitor_evt_ciclo_por_idx'),
        ),
        
        # CicloFacturacion model indexes
        migrations.AddIndex(
            model_name='ciclofacturacion',
            index=models.Index(fields=['mes', 'anio'], name='monitor_cic_mes_anio_idx'),
        ),
    ]
