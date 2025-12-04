from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import uuid
import pandas as pd
import io
from datetime import datetime

from app.database import get_db
from app.models.transaction import Transaction, TransactionType
from app.models.user_fund import Fund
from app.schemas.generated import (
    TransactionCreate,
    TransactionResponse,
    PaginatedResponseTransactionResponse,
    APIResponseTransactionResponse,
    APIResponseTransactionImportResponse,
    APIResponseBalanceResponse,
    ResponseStatus,
    Meta,
    RateLimitInfo,
    AuthTokens
)

router = APIRouter(
    prefix="/api/v1/transactions",
    tags=["transactions"]
)

# Helper to create standard response
def create_response(data, status=ResponseStatus.success, message=None, meta=None):
    return {
        "status": status,
        "data": data,
        "message": message,
        "meta": meta,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("", response_model=PaginatedResponseTransactionResponse)
def list_transactions(
    fund_id: uuid.UUID,
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.fund_id == fund_id)
    
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    
    transactions = query.order_by(Transaction.transaction_date.desc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()
        
    return create_response(
        data=transactions,
        meta=Meta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages
        )
    )

@router.post("", response_model=APIResponseTransactionResponse, status_code=201)
def create_transaction(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db)
):
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == transaction_in.fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
        
    transaction_data = transaction_in.model_dump()
    # Convert Pydantic Enum to SQLAlchemy Enum/String
    if hasattr(transaction_data['type'], 'value'):
        transaction_data['type'] = TransactionType(transaction_data['type'].value)
        
    transaction = Transaction(**transaction_data)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return create_response(data=transaction, message="Transaction created successfully")

@router.get("/balance", response_model=APIResponseBalanceResponse)
def get_balance(
    fund_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
        
    # Calculate balance: Sum(DEPOSIT) - Sum(WITHDRAWAL)
    deposits = db.query(func.sum(Transaction.amount)) \
        .filter(Transaction.fund_id == fund_id, Transaction.type == TransactionType.DEPOSIT) \
        .scalar() or 0
        
    withdrawals = db.query(func.sum(Transaction.amount)) \
        .filter(Transaction.fund_id == fund_id, Transaction.type == TransactionType.WITHDRAWAL) \
        .scalar() or 0
        
    balance = float(deposits) - float(withdrawals)
    
    return create_response(
        data={"balance": balance, "currency": "USD"}, # Assuming USD for now
        message="Balance calculated successfully"
    )

@router.put("/{transaction_id}", response_model=APIResponseTransactionResponse)
def update_transaction(
    transaction_id: uuid.UUID,
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db)
):
    # Verify transaction exists
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Update fields
    transaction_data = transaction_in.model_dump()
    # Convert Pydantic Enum to SQLAlchemy Enum
    if hasattr(transaction_data['type'], 'value'):
        transaction_data['type'] = TransactionType(transaction_data['type'].value)
    
    for key, value in transaction_data.items():
        setattr(transaction, key, value)
    
    db.commit()
    db.refresh(transaction)
    
    return create_response(data=transaction, message="Transaction updated successfully")

@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    # Verify transaction exists
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(transaction)
    db.commit()
    
    return create_response(data={"id": str(transaction_id)}, message="Transaction deleted successfully")

@router.post("/import", response_model=APIResponseTransactionImportResponse)
async def import_transactions(
    fund_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload Excel file.")

    contents = await file.read()
    
    try:
        # Read Excel - Header is at row index 2 (0-based) based on analysis
        df = pd.read_excel(io.BytesIO(contents), header=2)
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    imported_count = 0
    skipped_count = 0
    errors = []

    # Expected columns: 'Transaction Date', 'Transaction Type', 'Amount', 'Status', etc.
    required_columns = ['Transaction Date', 'Transaction Type', 'Amount']
    if not all(col in df.columns for col in required_columns):
         raise HTTPException(status_code=400, detail=f"Missing required columns. Expected: {required_columns}")

    for index, row in df.iterrows():
        try:
            # Parse Date
            date_str = str(row['Transaction Date'])
            try:
                # Example: 06/08/2019 23:08
                transaction_date = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
            except ValueError:
                # Fallback or skip
                skipped_count += 1
                errors.append(f"Row {index}: Invalid date format {date_str}")
                continue

            # Parse Type
            type_str = str(row['Transaction Type']).upper()
            if 'DEPOSIT' in type_str:
                trans_type = TransactionType.DEPOSIT
            elif 'WITHDRAW' in type_str:
                trans_type = TransactionType.WITHDRAWAL
            else:
                skipped_count += 1
                errors.append(f"Row {index}: Unknown transaction type {type_str}")
                continue

            # Parse Amount
            amount_str = str(row['Amount'])
            # Remove currency symbol and commas (e.g. AU$50.00)
            # Simple regex or replace
            import re
            amount_clean = re.sub(r'[^\d.]', '', amount_str)
            try:
                amount = float(amount_clean)
            except ValueError:
                skipped_count += 1
                errors.append(f"Row {index}: Invalid amount {amount_str}")
                continue

            # Check for duplicates (optional, based on date, type, amount, fund)
            exists = db.query(Transaction).filter(
                Transaction.fund_id == fund_id,
                Transaction.transaction_date == transaction_date,
                Transaction.type == trans_type,
                Transaction.amount == amount
            ).first()
            
            if exists:
                skipped_count += 1
                continue

            # Create Transaction
            transaction = Transaction(
                fund_id=fund_id,
                transaction_date=transaction_date,
                type=trans_type,
                amount=amount,
                currency="USD", # Defaulting to USD, logic to parse currency from string could be added
                status=str(row.get('Status', 'COMPLETED')),
                reference=str(row.get('Report', '')), # Using Report as reference? Or maybe generated ID
                description=f"Imported from {file.filename}",
                payment_method=str(row.get('Payment Method', '')),
                trading_account=str(row.get('Trading Account', ''))
            )
            db.add(transaction)
            imported_count += 1
            
        except Exception as e:
            skipped_count += 1
            errors.append(f"Row {index}: Error {str(e)}")

    db.commit()

    return create_response(
        data={
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors
        },
        message="Import completed"
    )
