import { OpenInterestUpload } from '@/components/data/OpenInterestUpload';

export default function OpenInterestPage() {
    return (
        <div className="container mx-auto py-8">
            <h1 className="text-3xl font-bold mb-6">Open Interest Data</h1>
            
            <div className="grid gap-6 md:grid-cols-2">
                <div>
                    <h2 className="text-xl font-semibold mb-4">Upload Data</h2>
                    <OpenInterestUpload />
                </div>
                
                <div>
                     <h2 className="text-xl font-semibold mb-4">Historical Data</h2>
                     <p className="text-muted-foreground">Visualization coming soon...</p>
                     {/* Placeholder for Data Table/Chart */}
                </div>
            </div>
        </div>
    );
}
