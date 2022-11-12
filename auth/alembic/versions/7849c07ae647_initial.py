"""initial

Revision ID: 7849c07ae647
Revises: 
Create Date: 2022-11-11 23:59:03.094652

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7849c07ae647'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('create schema auth')
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('service',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('key', sa.String(length=256), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.Integer(), nullable=False),
    sa.Column('login', sa.String(length=32), nullable=False),
    sa.Column('password', sa.String(length=128), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login'),
    schema='auth'
    )
    op.create_table('login_attempt',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('fingerprint', sa.String(length=256), nullable=False),
    sa.Column('date_time', sa.DateTime(), nullable=False),
    sa.Column('response', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('login_session',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('start', sa.DateTime(), nullable=False),
    sa.Column('end', sa.DateTime(), nullable=False),
    sa.Column('stopped', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('permission',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['service_id'], ['auth.service.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('access_attempt',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('login_session_id', sa.Integer(), nullable=True),
    sa.Column('fingerprint', sa.String(length=256), nullable=False),
    sa.Column('date_time', sa.DateTime(), nullable=False),
    sa.Column('response', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['login_session_id'], ['auth.login_session.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('access_session',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('login_session_id', sa.Integer(), nullable=False),
    sa.Column('start', sa.DateTime(), nullable=False),
    sa.Column('end', sa.DateTime(), nullable=False),
    sa.Column('stopped', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['login_session_id'], ['auth.login_session.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('user_permission',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Integer(), nullable=False),
    sa.Column('given_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['permission_id'], ['auth.permission.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'permission_id'),
    schema='auth'
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_permission', schema='auth')
    op.drop_table('access_session', schema='auth')
    op.drop_table('access_attempt', schema='auth')
    op.drop_table('permission', schema='auth')
    op.drop_table('login_session', schema='auth')
    op.drop_table('login_attempt', schema='auth')
    op.drop_table('user', schema='auth')
    op.drop_table('service', schema='auth')
    # ### end Alembic commands ###
    op.execute('drop schema auth')
