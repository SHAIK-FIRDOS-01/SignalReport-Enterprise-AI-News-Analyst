import django.contrib.postgres.indexes
import django.contrib.postgres.search
import pgvector.django
from pgvector.django import VectorExtension
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge_base', '0007_delete_ingestionchannel_remove_notification_alert_and_more'),
    ]

    operations = [
        VectorExtension(),
        migrations.AddField(
            model_name='knowledgebasenode',
            name='metadata_json',
            field=models.JSONField(blank=True, default=dict, help_text='Structured funding amounts, arXiv IDs, benchmark scores, GitHub release tags'),
        ),
        migrations.AddField(
            model_name='knowledgebasenode',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='knowledgebasenode',
            name='signal_type',
            field=models.CharField(choices=[('LAUNCH', 'Product/Model Launch'), ('FUNDING', 'Startup Funding/M&A'), ('RESEARCH', 'Research Paper Breakthrough'), ('UPGRADE', 'Major Release/Upgrade'), ('BUZZ', 'Viral Tech Discussion'), ('GENERAL', 'General Tech Intelligence')], db_index=True, default='GENERAL', help_text='Categorized tech signal type (LAUNCH, FUNDING, RESEARCH, UPGRADE, BUZZ)', max_length=50),
        ),
        migrations.AddField(
            model_name='knowledgebasenode',
            name='tech_domain',
            field=models.CharField(db_index=True, default='General', help_text='Technology domain (e.g., AI/ML, Cloud, Security, Systems)', max_length=100),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='content_raw',
            field=models.TextField(blank=True, default='', help_text='Original unedited snippet from the source'),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='embedding_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], db_index=True, default='PENDING', max_length=20),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='embedding_vector',
            field=pgvector.django.vector.VectorField(blank=True, dimensions=384, help_text='384-dimension vector embedding (BAAI/bge-small-en-v1.5 via fastembed)', null=True),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='entities',
            field=models.JSONField(blank=True, default=list, help_text='Extracted entities (organizations, authors, tools)'),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='full_text_scraped',
            field=models.TextField(blank=True, help_text='Complete cleaned article body extracted in Markdown', null=True),
        ),
        migrations.AlterField(
            model_name='knowledgebasenode',
            name='published_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddIndex(
            model_name='knowledgebasenode',
            index=models.Index(fields=['signal_type'], name='kb_node_signal__695def_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebasenode',
            index=models.Index(fields=['tech_domain'], name='kb_node_tech_do_a8ea8a_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebasenode',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='kb_node_search__287a25_gin'),
        ),
    ]
