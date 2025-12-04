import Papa from 'papaparse';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Transaction } from '../api/types';

/**
 * Export transactions to CSV file
 */
export function exportToCSV(transactions: Transaction[], filename: string = 'transactions.csv') {
    const data = transactions.map(t => ({
        Date: new Date(t.transaction_date).toLocaleDateString(),
        Type: t.type,
        Amount: t.amount,
        Currency: t.currency,
        Status: t.status,
        Description: t.description || '',
        Reference: t.reference || '',
        'Payment Method': t.payment_method || '',
        'Trading Account': t.trading_account || '',
        'Created At': new Date(t.created_at).toLocaleString()
    }));

    const csv = Papa.unparse(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Export transactions to PDF file
 */
export function exportToPDF(
    transactions: Transaction[],
    balance: number,
    currency: string,
    filename: string = 'transactions.pdf'
) {
    const doc = new jsPDF();
    
    // Title
    doc.setFontSize(18);
    doc.text('Transaction Report', 14, 22);
    
    // Balance Summary
    doc.setFontSize(12);
    doc.text(`Current Balance: ${currency} ${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 14, 32);
    doc.text(`Total Transactions: ${transactions.length}`, 14, 38);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 44);
    
    // Transaction Table
    const tableData = transactions.map(t => [
        new Date(t.transaction_date).toLocaleDateString(),
        t.type,
        `${t.currency} ${t.amount.toFixed(2)}`,
        t.status,
        t.description || '-'
    ]);
    
    autoTable(doc, {
        head: [['Date', 'Type', 'Amount', 'Status', 'Description']],
        body: tableData,
        startY: 50,
        styles: { fontSize: 9 },
        headStyles: { fillColor: [41, 128, 185] }
    });
    
   doc.save(filename);
}
