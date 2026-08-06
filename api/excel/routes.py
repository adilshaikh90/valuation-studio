from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from ..auth.utils import get_current_user
from ..company.data_fetcher import CompanyDataFetcher
from .generator import generate_financial_model
import io
from datetime import datetime

router = APIRouter(prefix='/api/excel', tags=['excel'])
data_fetcher = CompanyDataFetcher()

@router.get('/{ticker}/download')
async def download_excel(ticker: str, current_user = Depends(get_current_user)):
    ticker = ticker.upper()
    buffer = generate_financial_model(ticker, data_fetcher)
    
    company_info = data_fetcher.get_company_info(ticker)
    company_name = company_info.get('name', ticker).replace(' ', '_')
    filename = f"{company_name}_Financial_Model_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
