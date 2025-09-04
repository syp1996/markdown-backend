from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile, status)
from sqlalchemy.orm import Session
from sqlalchemy import text

# 个人使用版本，无需认证
from app.database import get_db
from app.models import Document, User
from app.schemas import (DocumentCreate, DocumentResponse, DocumentUpdate,
                         MessageResponse, PaginatedResponse,
                         DocumentSearchResponse, DocumentSearchResult, SearchHighlight)

router = APIRouter()

def _generate_highlights(document: Document, search_term: str) -> SearchHighlight:
    """生成搜索结果高亮"""
    import re
    
    def highlight_text(text: str, term: str, max_length: int = 200) -> str:
        if not text or not term:
            return text
        
        # 创建不区分大小写的正则表达式
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        
        # 找到匹配位置
        matches = list(pattern.finditer(text))
        if not matches:
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # 选择第一个匹配位置附近的文本
        match = matches[0]
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        # 高亮匹配文本
        highlighted = pattern.sub(f'<mark>\\g<0></mark>', snippet)
        return highlighted
    
    highlights = SearchHighlight()
    
    if document.title and search_term.lower() in document.title.lower():
        highlights.title = highlight_text(document.title, search_term, 100)
    
    if document.excerpt and search_term.lower() in document.excerpt.lower():
        highlights.excerpt = highlight_text(document.excerpt, search_term, 200)
    
    if document.content_text and search_term.lower() in document.content_text.lower():
        highlights.content_preview = highlight_text(document.content_text, search_term, 300)
    
    return highlights

def _generate_content_preview(content_text: str, search_term: str, max_length: int = 200) -> str:
    """生成内容预览"""
    if not content_text:
        return ""
    
    # 移除HTML标签
    import re
    clean_text = re.sub(r'<[^>]+>', '', content_text)
    
    if not search_term:
        return clean_text[:max_length] + "..." if len(clean_text) > max_length else clean_text
    
    # 查找关键词位置
    term_pos = clean_text.lower().find(search_term.lower())
    if term_pos == -1:
        return clean_text[:max_length] + "..." if len(clean_text) > max_length else clean_text
    
    # 围绕关键词生成预览
    start = max(0, term_pos - 50)
    end = min(len(clean_text), term_pos + len(search_term) + 50)
    
    preview = clean_text[start:end]
    if start > 0:
        preview = "..." + preview
    if end < len(clean_text):
        preview = preview + "..."
    
    return preview

@router.post("/documents/upload", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    type: str = Form("markdown"),
    db: Session = Depends(get_db)
):
    """上传Markdown文档 - 个人使用版本，无需认证"""
    # 检查文件类型
    if not file.filename.endswith('.md'):
        raise HTTPException(status_code=400, detail="只支持Markdown文件(.md)")
    
    # 读取文件内容
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")
    
    # 生成slug
    base_slug = title.lower().replace(' ', '-').replace('_', '-')
    unique_slug = base_slug
    counter = 1
    
    # 检查slug是否已存在
    while db.query(Document).filter(Document.slug == unique_slug).first():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1
    
    # 获取或创建默认用户
    default_user = db.query(User).filter(User.username == "default_user").first()
    if not default_user:
        default_user = User(
            username="default_user",
            email="default@example.com",
            is_admin=False
        )
        default_user.set_password("default_password_123")
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
    
    # 创建文档（不包含content_text字段，因为它是生成列）
    document = Document(
        title=title,
        content={"markdown": content_str, "type": type},  # 将内容存储为JSON格式
        slug=unique_slug,
        status=0,  # draft
        user_id=default_user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return MessageResponse(
        message="文档上传成功",
        data=DocumentResponse.from_orm(document)
    )

@router.get("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(
    keyword: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=50, description="每页数量"),
    search_mode: str = Query("basic", pattern="^(basic|fulltext)$", description="搜索模式"),
    highlight: bool = Query(True, description="是否高亮显示匹配文本"),
    db: Session = Depends(get_db)
):
    """高级搜索文档 - 支持全文搜索和相关度排序"""
    import time
    start_time = time.time()
    
    try:
        if search_mode == "fulltext":
            # 使用MySQL全文搜索
            
            # 构建全文搜索查询
            search_query = text("""
                SELECT *, 
                MATCH(title, excerpt, content_text) AGAINST(:search_term IN NATURAL LANGUAGE MODE) as relevance_score
                FROM documents 
                WHERE deleted_at IS NULL 
                AND MATCH(title, excerpt, content_text) AGAINST(:search_term IN NATURAL LANGUAGE MODE)
                ORDER BY relevance_score DESC, updated_at DESC
                LIMIT :offset, :limit
            """)
            
            count_query = text("""
                SELECT COUNT(*) as total
                FROM documents 
                WHERE deleted_at IS NULL 
                AND MATCH(title, excerpt, content_text) AGAINST(:search_term IN NATURAL LANGUAGE MODE)
            """)
            
            # 执行查询
            offset = (page - 1) * per_page
            results = db.execute(search_query, {
                'search_term': keyword,
                'offset': offset,
                'limit': per_page
            }).fetchall()
            
            total_result = db.execute(count_query, {'search_term': keyword}).fetchone()
            total = total_result.total if total_result else 0
            
        else:
            # 基础LIKE搜索（向后兼容）
            query = db.query(Document).filter(Document.deleted_at.is_(None))
            
            search_filter = (
                Document.title.contains(keyword) |
                Document.excerpt.contains(keyword) |
                Document.content_text.contains(keyword)
            )
            
            query = query.filter(search_filter)
            query = query.order_by(
                (~Document.title.contains(keyword)).asc(),
                (~Document.excerpt.contains(keyword)).asc(),
                Document.updated_at.desc()
            )
            
            total = query.count()
            results = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 处理搜索结果
        search_results = []
        
        if search_mode == "fulltext":
            for row in results:
                # 手动构建Document对象的字典表示
                doc_dict = {
                    'id': row.id,
                    'user_id': row.user_id,
                    'category_id': row.category_id,
                    'title': row.title,
                    'excerpt': row.excerpt,
                    'content': row.content if isinstance(row.content, dict) else None,
                    'slug': row.slug,
                    'status': row.status,
                    'is_pinned': bool(row.is_pinned),
                    'author_username': None,  # 需要单独查询
                    'category_name': None,   # 需要单独查询
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                    'deleted_at': row.deleted_at.isoformat() if row.deleted_at else None
                }
                
                # 创建临时Document对象用于高亮生成
                temp_doc = Document()
                temp_doc.title = row.title
                temp_doc.excerpt = row.excerpt
                temp_doc.content_text = row.content_text
                
                # 创建搜索结果
                result = DocumentSearchResult(
                    **doc_dict,
                    relevance_score=getattr(row, 'relevance_score', None),
                    highlights=_generate_highlights(temp_doc, keyword) if highlight else None,
                    content_preview=_generate_content_preview(row.content_text, keyword)
                )
                search_results.append(result)
        else:
            for doc in results:
                result = DocumentSearchResult(
                    **doc.to_dict(),
                    highlights=_generate_highlights(doc, keyword) if highlight else None,
                    content_preview=_generate_content_preview(doc.content_text, keyword)
                )
                search_results.append(result)
        
        search_time = (time.time() - start_time) * 1000
        pages = (total + per_page - 1) // per_page
        
        return DocumentSearchResponse(
            items=search_results,
            total=total,
            pages=pages,
            current_page=page,
            per_page=per_page,
            keyword=keyword,
            search_mode=search_mode,
            search_time_ms=round(search_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

@router.get("/documents", response_model=PaginatedResponse)
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[int] = Query(None, ge=0, le=2, description="状态筛选"),
    category_id: Optional[int] = Query(None, description="分类ID筛选"),
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    query = db.query(Document).filter(Document.deleted_at.is_(None))
    
    if status is not None:
        query = query.filter(Document.status == status)
    
    if category_id is not None:
        query = query.filter(Document.category_id == category_id)
    
    # 按创建时间倒序排列
    query = query.order_by(Document.created_at.desc())
    
    # 分页
    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    return PaginatedResponse(
        items=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        pages=pages,
        current_page=page,
        per_page=per_page
    )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """获取单个文档"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return DocumentResponse.from_orm(document)

@router.post("/documents", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    db: Session = Depends(get_db)
):
    """创建文档 - 个人使用版本，无需认证"""
    try:
        # 获取或创建默认用户
        default_user = db.query(User).filter(User.username == "default_user").first()
        if not default_user:
            default_user = User(
                username="default_user",
                email="default@example.com",
                is_admin=False
            )
            default_user.set_password("default_password_123")
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        
        # 生成唯一的slug（如果没有提供）
        if not document_data.slug:
            base_slug = document_data.title.lower().replace(' ', '-').replace('_', '-')
            unique_slug = base_slug
            counter = 1
            
            # 检查slug是否已存在
            while db.query(Document).filter(Document.slug == unique_slug).first():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            # 创建文档数据副本并更新slug
            doc_data = document_data.dict()
            doc_data['slug'] = unique_slug
        else:
            doc_data = document_data.dict()
        
        # 创建文档（排除content_text字段，因为它是生成列）
        doc_data.pop('content_text', None)  # 移除content_text字段
        document = Document(
            **doc_data,
            user_id=default_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return MessageResponse(
            message="文档创建成功",
            data=DocumentResponse.from_orm(document)
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建文档失败: {str(e)}"
        )

@router.put("/documents/{document_id}", response_model=MessageResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """更新文档 - 个人使用版本，无需认证"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 更新字段
        update_data = document_update.dict(exclude_unset=True)
        
        # 如果更新了标题，检查是否需要更新slug
        if 'title' in update_data and not update_data.get('slug'):
            base_slug = update_data['title'].lower().replace(' ', '-').replace('_', '-')
            unique_slug = base_slug
            counter = 1
            
            # 检查slug是否已存在（排除当前文档）
            while db.query(Document).filter(
                Document.slug == unique_slug,
                Document.id != document_id
            ).first():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            update_data['slug'] = unique_slug
        
        for field, value in update_data.items():
            setattr(document, field, value)
        
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        
        return MessageResponse(
            message="文档更新成功",
            data=DocumentResponse.from_orm(document)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文档失败: {str(e)}"
        )

@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """删除文档（软删除）- 个人使用版本，无需认证"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 软删除
        document.deleted_at = datetime.now(timezone.utc)
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return MessageResponse(message="文档删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )

@router.post("/documents/{document_id}/publish", response_model=MessageResponse)
async def publish_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """发布文档 - 个人使用版本，无需认证"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        if document.status == 1:
            return MessageResponse(message="文档已经是发布状态")
        
        document.status = 1  # published
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return MessageResponse(message="文档发布成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发布文档失败: {str(e)}"
        )

@router.post("/documents/{document_id}/pin", response_model=MessageResponse)
async def toggle_pin_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """切换文档置顶状态 - 个人使用版本，无需认证"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        document.is_pinned = not document.is_pinned
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return MessageResponse(
            message=f"文档已{'置顶' if document.is_pinned else '取消置顶'}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换置顶状态失败: {str(e)}"
        )

@router.post("/documents/plugin", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_document_from_plugin(
    document_data: DocumentCreate,
    db: Session = Depends(get_db)
):
    """从Chrome插件创建文档（无需认证）"""
    # 获取或创建默认用户
    default_user = db.query(User).filter(User.username == "chrome_plugin_user").first()
    if not default_user:
        # 如果默认用户不存在，创建一个
        default_user = User(
            username="chrome_plugin_user",
            email="chrome_plugin@example.com",
            is_admin=False
        )
        default_user.set_password("chrome_plugin_password_123")
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
    
    # 生成唯一的slug
    base_slug = document_data.slug or document_data.title.lower().replace(' ', '-')
    unique_slug = base_slug
    counter = 1
    
    # 检查slug是否已存在，如果存在则添加数字后缀
    while db.query(Document).filter(Document.slug == unique_slug).first():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1
    
    # 创建文档数据副本并更新slug
    doc_data = document_data.dict()
    doc_data['slug'] = unique_slug
    doc_data.pop('content_text', None)  # 移除content_text字段，因为它是生成列
    
    document = Document(
        **doc_data,
        user_id=default_user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return MessageResponse(
        message="文档创建成功",
        data=DocumentResponse.from_orm(document)
    )
