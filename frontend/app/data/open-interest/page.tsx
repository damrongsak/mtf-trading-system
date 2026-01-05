import { OpenInterestUpload } from '@/components/data/OpenInterestUpload';
import { OpenInterestHistory } from '@/components/data/OpenInterestHistory';
import { OpenInterestHeatmap } from '@/components/data/OpenInterestHeatmap';
import { OpenInterestAnalytics } from '@/components/data/OpenInterestAnalytics';

export default function OpenInterestPage() {
    return (
        <div className="container mx-auto py-8">
            <h1 className="text-3xl font-bold mb-6">Open Interest Data</h1>
            
            <div className="grid gap-6 md:grid-cols-2 lg:h-[600px]">
                <div className="h-full">
                    <OpenInterestUpload />
                </div>
                
                <div className="h-full">
                     <OpenInterestHistory />
                </div>
            </div>
            
            <div className="mt-8">
                <OpenInterestAnalytics />
            </div>
        </div>
    );
}
