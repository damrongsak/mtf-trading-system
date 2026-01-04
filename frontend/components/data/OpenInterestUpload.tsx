"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { uploadOpenInterest } from '@/lib/api/data';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function OpenInterestUpload() {
    const [file, setFile] = useState<File | null>(null);
    const [snapshotAt, setSnapshotAt] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setMessage({ type: 'error', text: "Please select a file." });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const date = snapshotAt ? new Date(snapshotAt) : undefined;
            const result = await uploadOpenInterest(file, date);
            setMessage({ 
                type: 'success', 
                text: `Successfully imported ${result.records_processed} records for ${result.snapshot_at}` 
            });
            setFile(null);
            // Reset file input manually if needed or just let it stay
        } catch (error: any) {
             setMessage({ 
                type: 'error', 
                text: error.message || "Upload failed" 
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="w-full max-w-md">
            <CardHeader>
                <CardTitle>Import Open Interest Data</CardTitle>
                <CardDescription>Upload Excel matrix file (.xlsx)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="file">Excel File</Label>
                    <Input 
                        id="file" 
                        type="file" 
                        accept=".xlsx" 
                        onChange={handleFileChange} 
                    />
                </div>
                
                <div className="space-y-2">
                    <Label htmlFor="snapshot-at">Snapshot Time (Optional)</Label>
                    <Input 
                        id="snapshot-at" 
                        type="datetime-local" 
                        value={snapshotAt}
                        onChange={(e) => setSnapshotAt(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                        Leave blank to use sheet name or current time.
                    </p>
                </div>

                {message && (
                    <Alert variant={message.type === 'error' ? 'destructive' : 'default'} className={message.type === 'success' ? "border-green-500 text-green-500" : ""}>
                         <AlertTitle>{message.type === 'success' ? "Success" : "Error"}</AlertTitle>
                         <AlertDescription>{message.text}</AlertDescription>
                    </Alert>
                )}

                <Button 
                    className="w-full" 
                    onClick={handleUpload} 
                    disabled={!file || loading}
                >
                    {loading ? "Uploading..." : "Upload"}
                </Button>
            </CardContent>
        </Card>
    );
}
