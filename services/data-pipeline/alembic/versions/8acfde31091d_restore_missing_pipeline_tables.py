"""Restore missing pipeline tables

Revision ID: 8acfde31091d
Revises: b5727db261b4
Create Date: 2026-03-06 11:06:17.700310

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8acfde31091d'
down_revision = 'b5727db261b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### economic_events ###
    op.create_table('economic_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('impact', sa.String(), nullable=False),
        sa.Column('datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual', sa.String(), nullable=True),
        sa.Column('forecast', sa.String(), nullable=True),
        sa.Column('previous', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_economic_events_datetime'), 'economic_events', ['datetime'], unique=False)
    op.create_index(op.f('ix_economic_events_external_id'), 'economic_events', ['external_id'], unique=True)
    op.create_index(op.f('ix_economic_events_id'), 'economic_events', ['id'], unique=False)

    # ### news_articles ###
    op.create_table('news_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_articles_external_id'), 'news_articles', ['external_id'], unique=True)
    op.create_index(op.f('ix_news_articles_published_at'), 'news_articles', ['published_at'], unique=False)
    op.create_index(op.f('ix_news_articles_symbol'), 'news_articles', ['symbol'], unique=False)

    # ### cot_records ###
    op.create_table('cot_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('report_date', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('commercials_long', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('commercials_short', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('non_commercials_long', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('non_commercials_short', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('managed_money_long', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('managed_money_short', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('non_reportable_long', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('non_reportable_short', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'report_date', name='uq_cot_records_symbol_report_date')
    )
    op.create_index('ix_cot_records_report_date', 'cot_records', ['report_date'], unique=False)
    op.create_index('ix_cot_records_symbol', 'cot_records', ['symbol'], unique=False)


def downgrade() -> None:
    op.drop_table('cot_records')
    op.drop_table('news_articles')
    op.drop_table('economic_events')
