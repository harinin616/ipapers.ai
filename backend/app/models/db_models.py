from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, Table, ForeignKey, ARRAY, Text, Date,BigInteger, Boolean, Identity
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID,JSONB
from pgvector.sqlalchemy import Vector
import uuid
from sqlalchemy import event


Base = declarative_base()

# Paper category association table
paper_categories = Table(
    'paper_categories',
    Base.metadata,
    Column('paper_id', String, primary_key=True),
    Column('platform', String, primary_key=True, default='arxiv'),
    Column('category', String, ForeignKey('categories.name'), primary_key=True),
    sa.ForeignKeyConstraint(['paper_id', 'platform'], ['papers.paper_id', 'papers.platform'], ondelete='CASCADE')
)

# Paper author association table with order
paper_authors = Table(
    'paper_authors',
    Base.metadata,
    Column('paper_id', String, primary_key=True),
    Column('platform', String, primary_key=True, default='arxiv'),
    Column('author', String, ForeignKey('authors.name'), primary_key=True),
    Column('author_order', Integer, nullable=False, default=0),
    sa.ForeignKeyConstraint(['paper_id', 'platform'], ['papers.paper_id', 'papers.platform'], ondelete='CASCADE')
)

class DBPaper(Base):
    __tablename__ = "papers"
    
    paper_id = Column(String, primary_key=True, index=True)
    platform = Column(String, primary_key=True, nullable=False, server_default='arxiv')
    title = Column(String, nullable=False)
    abstract = Column(Text, nullable=False)
    pdf_url = Column(String, nullable=False)
    published_date = Column(DateTime, nullable=False)
    updated_date = Column(DateTime, nullable=True)
    click_count = Column(Integer, nullable=False, default=0)
    embedding = Column(Vector(768), nullable=True)
    authors = relationship(
        "DBAuthor", 
        secondary=paper_authors, 
        backref="papers",
        order_by=paper_authors.c.author_order
    )
    categories = relationship("DBCategory", secondary=paper_categories, backref="papers")
    def __repr__(self):
        return f"<Paper {self.paper_id} ({self.platform}): {self.title}>"


class DBAuthor(Base):
    """Paper author database model"""
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    
    def __repr__(self):
        return f"<Author {self.name}>"

class DBCategory(Base):
    """Paper category database model"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    
    def __repr__(self):
        return f"<Category {self.name}>"

class DBFolder(Base):
    __tablename__ = "folders"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    name       = Column(String(64), nullable=False, default="default")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    user  = relationship("DBUser", back_populates="folders")
    files = relationship(
        "DBUserFile",
        back_populates="folder",
        cascade="all, delete-orphan",
        order_by="DBUserFile.added_at"
    )

    def __repr__(self):
        return f"<Folder {self.name} (user={self.user_id})>"

class DBUserFile(Base):
    __tablename__ = 'user_files'

    id        = Column(Integer, primary_key=True, autoincrement=True)
    folder_id = Column(Integer, ForeignKey('folders.id', ondelete='CASCADE'), nullable=False, index=True)
    paper_id  = Column(String, nullable=False, index=True)
    platform  = Column(String, nullable=False, server_default=sa.text("'arxiv'"))
    added_at  = Column(DateTime, nullable=False, default=datetime.utcnow)
    selected  = Column(Boolean, nullable=False, server_default=sa.text("false"))

    # 关系
    folder = relationship('DBFolder', back_populates='files')
    paper  = relationship('DBPaper', foreign_keys=[paper_id, platform], 
                         primaryjoin="and_(DBUserFile.paper_id==DBPaper.paper_id, "
                                    "DBUserFile.platform==DBPaper.platform)")

    __table_args__ = (
        sa.UniqueConstraint('folder_id', 'paper_id', 'platform', name='uq_folder_paper_platform'),
        sa.ForeignKeyConstraint(['paper_id', 'platform'], ['papers.paper_id', 'papers.platform'], 
                              name='fk_user_files_paper_platform', ondelete='CASCADE'),
    )

    def __repr__(self):
        return f"<UserFile folder={self.folder_id} paper={self.paper_id} ({self.platform})>"



class DBUser(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # 新主键
    legacy_user_id = Column(Integer, Identity(), unique=True, nullable=False)

    name = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True, index=True)

    folders = relationship(
        "DBFolder",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DBFolder.created_at",
    )
    topics = relationship(
        "DBUserTopic",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DBUserTopic.topic",
    )
    sessions = relationship("DBSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.id}: {self.name}>"

class DBUserTopic(Base):
    __tablename__ = "user_topics"
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    topic   = Column(String,  primary_key=True, index=True)

    user = relationship('DBUser', back_populates='topics')

class DBSession(Base):
    """Chat session database model"""
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String, nullable=False, default="untitled")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship("DBUser", back_populates="sessions")
    messages = relationship("DBMessage", back_populates="session", cascade="all, delete-orphan", order_by="DBMessage.created_at")
    
    def __repr__(self):
        return f"<Session {self.session_id}: User {self.user_id}>"

class DBMessage(Base):
    """Chat message database model"""
    __tablename__ = "messages"
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system', etc.
    
    # Relationships
    session = relationship("DBSession", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.message_id}: {self.role} in Session {self.session_id}>"

class PageViewDaily(Base):
    __tablename__ = "page_view_daily"
    day  = Column(Date, primary_key=True, index=True)
    cnt  = Column(BigInteger, nullable=False)

# 在 models.py 末尾或合适位置添加
class DBFeedback(Base):
    """Contact-Us / Feedback 表"""
    __tablename__ = "feedback"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    question   = Column(Text,    nullable=False)
    email      = Column(String(100), nullable=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class DBEmailList(Base):
    """A standalone table that stores unique email addresses only."""
    __tablename__ = "email_list"

    email = Column(String(320), primary_key=True, unique=True, index=True)  # RFC 5321 max length

    def __repr__(self):
        return f"<Email {self.email}>"

class DBSharedFolder(Base):
    __tablename__ = "shared_folders"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    folder_id  = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=False)
    owner_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_public  = Column(Boolean, nullable=False, server_default=sa.text("true"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 新增字段：概要，可为空
    summary    = Column(Text, nullable=True)

    # ⭐ 新增字段：可访问用户列表（ARRAY<uuid>）
    allowed_user_ids = Column(
        ARRAY(UUID(as_uuid=True)),                        # 列类型
        nullable=False,
        server_default=sa.text("ARRAY[]::uuid[]")        # PG 侧空数组默认
    )
    allowed_editor_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=sa.text("ARRAY[]::uuid[]")
    )

    folder = relationship("DBFolder")
    owner  = relationship("DBUser")

    def __repr__(self):
        return f"<Share#{self.id} → Folder {self.folder_id}>"

# ---- 自动把 owner_id 塞进 allowed_user_ids -------------------------
@event.listens_for(DBSharedFolder, "before_insert")
def _add_owner_to_allowed(mapper, connection, target):
    if target.allowed_user_ids is None or len(target.allowed_user_ids) == 0:
        target.allowed_user_ids = [target.owner_id]
    elif target.owner_id not in target.allowed_user_ids:
        target.allowed_user_ids.append(target.owner_id)



shared_folder_comments = Table(
    "shared_folder_comments",
    Base.metadata,
    Column(
        "shared_folder_id",
        Integer,
        ForeignKey("shared_folders.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "comment_id",
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        primary_key=True
    )
)

# —— 2. 单独定义评论表 —— #
class DBComment(Base):
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # 不在这里定义 shared_folder_id 外键
        # —— 新增：评论者 ID 和 名字 —— #
    commenter_id     = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    commenter_name   = Column(
        String(100),
        nullable=False,
        server_default=""
    )

    # —— 外键关系 —— #
    commenter        = relationship("DBUser", lazy="joined")

    def __repr__(self):
        return f"<Comment#{self.id}>"

DBSharedFolder.comments = relationship(
    "DBComment",
    secondary=shared_folder_comments,
    back_populates="shared_folders",
    cascade="save-update, merge, delete",
    passive_deletes=True
)

# 给 DBComment 添加 .shared_folders
DBComment.shared_folders = relationship(
    "DBSharedFolder",
    secondary=shared_folder_comments,
    back_populates="comments"
)