'use client';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    perPage: number;
    total: number;
    onPageChange: (page: number) => void;
    onPerPageChange?: (perPage: number) => void;
}

export function Pagination({
    currentPage,
    totalPages,
    perPage,
    total,
    onPageChange,
    onPerPageChange
}: PaginationProps) {
    const startItem = ((currentPage - 1) * perPage) + 1;
    const endItem = Math.min(currentPage * perPage, total);

    const getPageNumbers = () => {
        const pages: (number | string)[] = [];
        const maxVisible = 5;

        if (totalPages <= maxVisible) {
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            if (currentPage <= 3) {
                for (let i = 1; i <= 4; i++) pages.push(i);
                pages.push('...');
                pages.push(totalPages);
            } else if (currentPage >= totalPages - 2) {
                pages.push(1);
                pages.push('...');
                for (let i = totalPages - 3; i <= totalPages; i++) pages.push(i);
            } else {
                pages.push(1);
                pages.push('...');
                pages.push(currentPage - 1);
                pages.push(currentPage);
                pages.push(currentPage + 1);
                pages.push('...');
                pages.push(totalPages);
            }
        }

        return pages;
    };

    if (total === 0) return null;

    return (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
            {/* Info */}
            <div className="flex items-center gap-4">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                    Showing <span className="font-medium">{startItem}</span> to{' '}
                    <span className="font-medium">{endItem}</span> of{' '}
                    <span className="font-medium">{total}</span> results
                </p>

                {/* Per Page Selector */}
                {onPerPageChange && (
                    <div className="flex items-center gap-2">
                        <label htmlFor="perPage" className="text-sm text-gray-700 dark:text-gray-300">
                            Per page:
                        </label>
                        <select
                            id="perPage"
                            value={perPage}
                            onChange={(e) => onPerPageChange(Number(e.target.value))}
                            className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        >
                            <option value={10}>10</option>
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                            <option value={100}>100</option>
                        </select>
                    </div>
                )}
            </div>

            {/* Page Controls */}
            <div className="flex items-center gap-1">
                {/* First Page */}
                <button
                    onClick={() => onPageChange(1)}
                    disabled={currentPage === 1}
                    className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="First page"
                >
                    ««
                </button>

                {/* Previous Page */}
                <button
                    onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Previous
                </button>

                {/* Page Numbers */}
                {getPageNumbers().map((page, index) =>
                    typeof page === 'number' ? (
                        <button
                            key={index}
                            onClick={() => onPageChange(page)}
                            className={`px-3 py-1 text-sm border rounded ${
                                page === currentPage
                                    ? 'bg-primary text-white border-primary'
                                    : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
                            }`}
                        >
                            {page}
                        </button>
                    ) : (
                        <span key={index} className="px-2 text-gray-500">
                            {page}
                        </span>
                    )
                )}

                {/* Next Page */}
                <button
                    onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next
                </button>

                {/* Last Page */}
                <button
                    onClick={() => onPageChange(totalPages)}
                    disabled={currentPage === totalPages}
                    className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Last page"
                >
                    »»
                </button>
            </div>
        </div>
    );
}
