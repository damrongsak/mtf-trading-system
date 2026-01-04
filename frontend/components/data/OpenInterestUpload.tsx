"use client";

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone'; // Assuming usage, if not installed I will use native events or install it. Ah, I should stick to native to avoid dep issues if possible, or check if I can use generic drag/drop.
// Actually, standard drag/drop is easy. 
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { uploadOpenInterest } from '@/lib/api/data';
import { 
    UploadCloud, 
    FileSpreadsheet, 
    Calendar, 
    CheckCircle2, 
    AlertCircle, 
    X, 
    Loader2 
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function OpenInterestUpload() {
    const [file, setFile] = useState<File | null>(null);
    const [snapshotAt, setSnapshotAt] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const onDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const onDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const onDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile.name.endsWith('.xlsx')) {
                setFile(droppedFile);
                setMessage(null);
            } else {
                setMessage({ type: 'error', text: "Only .xlsx files are allowed." });
            }
        }
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setMessage(null);
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
                text: `Successfully imported ${result.records_processed} records` 
            });
            setFile(null); // Clear file on success
        } catch (error: any) {
             setMessage({ 
                type: 'error', 
                text: error.message || "Upload failed. Please check the file format." 
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="w-full h-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl">
            <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-accent-blue/10 rounded-lg">
                         <UploadCloud className="w-6 h-6 text-accent-blue" />
                    </div>
                    <div>
                        <CardTitle className="text-xl">Import Data</CardTitle>
                        <CardDescription>Upload Open Interest Matrix (.xlsx)</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                
                {/* Drag & Drop Zone */}
                <div 
                    className={cn(
                        "relative group cursor-pointer flex flex-col items-center justify-center w-full h-48 rounded-xl border-2 border-dashed transition-all duration-300",
                        isDragging 
                            ? "border-accent-blue bg-accent-blue/5" 
                            : file 
                                ? "border-accent-green/50 bg-accent-green/5" 
                                : "border-gray-800 hover:border-gray-700 hover:bg-gray-900/50"
                    )}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                    onClick={() => document.getElementById('file-upload')?.click()}
                >
                    <input 
                        id="file-upload" 
                        type="file" 
                        className="hidden" 
                        accept=".xlsx" 
                        onChange={handleFileChange} 
                    />
                    
                    {file ? (
                        <div className="flex flex-col items-center text-center p-4 animate-in fade-in zoom-in duration-300">
                            <div className="w-12 h-12 bg-accent-green/20 rounded-full flex items-center justify-center mb-3">
                                <FileSpreadsheet className="w-6 h-6 text-accent-green" />
                            </div>
                            <p className="text-sm font-medium text-white truncate max-w-[200px]">{file.name}</p>
                            <p className="text-xs text-gray-500 mt-1">{(file.size / 1024).toFixed(0)} KB</p>
                            <Button 
                                variant="ghost" 
                                size="sm"
                                className="mt-2 text-gray-400 hover:text-red-400"
                                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                            >
                                <X className="w-4 h-4 mr-1" /> Remove
                            </Button>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center text-center p-4">
                            <div className={cn(
                                "w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors",
                                isDragging ? "bg-accent-blue/20" : "bg-gray-900"
                            )}>
                                <UploadCloud className={cn(
                                    "w-6 h-6 transition-colors", 
                                    isDragging ? "text-accent-blue" : "text-gray-500 group-hover:text-gray-400"
                                )} />
                            </div>
                            <p className="text-sm font-medium text-gray-300">
                                {isDragging ? "Drop file here" : "Click to upload or drag & drop"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Excel files only (.xlsx)</p>
                        </div>
                    )}
                </div>

                {/* Optional Settings */}
                <div className="space-y-3">
                    <Label className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5" /> 
                        Configuration
                    </Label>
                    <div className="grid grid-cols-1 gap-4">
                        <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-800">
                             <div className="flex items-center justify-between mb-2">
                                <Label htmlFor="snapshot-at" className="text-sm text-gray-300">Snapshot Time</Label>
                                <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">Optional</span>
                             </div>
                             <input 
                                id="snapshot-at" 
                                type="datetime-local" 
                                className="w-full bg-gray-950 border border-gray-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-accent-blue transition-all"
                                value={snapshotAt}
                                onChange={(e) => setSnapshotAt(e.target.value)}
                             />
                             <p className="text-xs text-gray-600 mt-2">
                                Overrides the timestamp detected in the file (e.g., from sheet name).
                             </p>
                        </div>
                    </div>
                </div>

                {/* Feedback Messages */}
                {message && (
                    <Alert 
                        variant={message.type === 'error' ? 'destructive' : 'default'} 
                        className={cn(
                            "animate-in slide-in-from-bottom-2 fade-in",
                            message.type === 'success' 
                                ? "border-green-500/50 bg-green-500/10 text-green-400" 
                                : "border-red-500/50 bg-red-500/10 text-red-400"
                        )}
                    >
                         {message.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                         <AlertTitle>{message.type === 'success' ? "Success" : "Error"}</AlertTitle>
                         <AlertDescription>{message.text}</AlertDescription>
                    </Alert>
                )}

                <Button 
                    className={cn(
                        "w-full h-11 font-medium transition-all duration-300",
                        loading ? "cursor-not-allowed opacity-80" : "hover:scale-[1.02]"
                    )}
                    variant={file ? "default" : "secondary"}
                    onClick={handleUpload} 
                    disabled={!file || loading}
                >
                    {loading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing...
                        </>
                    ) : (
                        "Start Import"
                    )}
                </Button>
            </CardContent>
        </Card>
    );
}
