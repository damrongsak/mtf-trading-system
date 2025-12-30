'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { createFund, updateFund, deleteFund, type Fund } from '@/lib/api/fund';
import { Loader2, Plus, Trash2, Edit } from "lucide-react";
import { ConfirmationModal } from "@/components/ui/confirmation-modal";

interface FundManagementModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
    funds: Fund[];
    currentFundId: string | null;
}

export function FundManagementModal({ isOpen, onClose, onSuccess, funds, currentFundId }: FundManagementModalProps) {
    const [activeTab, setActiveTab] = useState('create');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Create State
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');

    // Edit State
    const [editId, setEditId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');
    const [editDescription, setEditDescription] = useState('');

    // Delete State
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        if (currentFundId) {
            setEditId(currentFundId);
            const fund = funds.find(f => f.id === currentFundId);
            if (fund) {
                setEditName(fund.name);
                setEditDescription(fund.description || '');
            }
        }
    }, [currentFundId, funds, isOpen]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await createFund({ name: newName, description: newDescription });
            setNewName('');
            setNewDescription('');
            onSuccess();
            onClose();
        } catch (err) {
            setError((err as Error).message || "Failed to create fund");
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editId) return;
        setLoading(true);
        setError(null);

        try {
            await updateFund(editId, { name: editName, description: editDescription });
            onSuccess();
        } catch (err) {
            setError((err as Error).message || "Failed to update fund");
        } finally {
            setLoading(false);
        }
    };

    const confirmDelete = async () => {
        if (!deleteId) return;
        setIsDeleting(true);
        setError(null);
        
        try {
            await deleteFund(deleteId);
            onSuccess();
            // If current fund was deleted, selection logic in parent should handle it,
            // but we'll close the modal
            if (deleteId === editId) onClose();
        } catch (_err) {
            setError("Failed to delete fund. You might be the only owner or it has active data.");
        } finally {
            setIsDeleting(false);
            setDeleteId(null);
        }
    };

    return (
        <>
             <ConfirmationModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={confirmDelete}
                title="Delete Fund"
                message="Are you sure you want to delete this fund? This action cannot be undone and may affect associated data."
                confirmText="Delete Fund"
                isLoading={isDeleting}
                variant="destructive"
            />

            <Dialog open={isOpen} onOpenChange={onClose}>
                <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Fund Management</DialogTitle>
                    </DialogHeader>

                    {error && (
                        <div className="p-3 bg-red-900/20 border border-red-900/50 rounded-md text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-2 bg-gray-800">
                            <TabsTrigger value="create">Create New</TabsTrigger>
                            <TabsTrigger value="edit">Edit Current</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="create" className="space-y-4 py-4">
                            <form onSubmit={handleCreate} className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Fund Name</Label>
                                    <Input 
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        placeholder="e.g. Primary Alpha Fund"
                                        required
                                        className="bg-gray-800 border-gray-700"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Description (Optional)</Label>
                                    <Input 
                                        value={newDescription}
                                        onChange={(e) => setNewDescription(e.target.value)}
                                        placeholder="Brief description of strategy/goal"
                                        className="bg-gray-800 border-gray-700"
                                    />
                                </div>
                                <Button type="submit" disabled={loading} className="w-full">
                                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Plus className="h-4 w-4 mr-2"/>}
                                    Create Fund
                                </Button>
                            </form>
                        </TabsContent>

                        <TabsContent value="edit" className="space-y-4 py-4">
                             <div className="space-y-2 mb-4">
                                <Label>Select Fund to Edit</Label>
                                <select 
                                    value={editId || ''}
                                    onChange={(e) => {
                                        const id = e.target.value;
                                        setEditId(id);
                                        const f = funds.find(x => x.id === id);
                                        if (f) {
                                            setEditName(f.name);
                                            setEditDescription(f.description || '');
                                        }
                                    }}
                                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md"
                                >
                                    <option value="" disabled>Select a fund...</option>
                                    {funds.map(f => (
                                        <option key={f.id} value={f.id}>{f.name}</option>
                                    ))}
                                </select>
                            </div>

                            {editId && (
                                <form onSubmit={handleUpdate} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label>Fund Name</Label>
                                        <Input 
                                            value={editName}
                                            onChange={(e) => setEditName(e.target.value)}
                                            required
                                            className="bg-gray-800 border-gray-700"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Description</Label>
                                        <Input 
                                            value={editDescription}
                                            onChange={(e) => setEditDescription(e.target.value)}
                                            className="bg-gray-800 border-gray-700"
                                        />
                                    </div>
                                    <div className="flex gap-2">
                                        <Button type="submit" disabled={loading} className="flex-1">
                                            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Edit className="h-4 w-4 mr-2"/>}
                                            Update Details
                                        </Button>
                                        <Button 
                                            type="button" 
                                            variant="destructive" 
                                            onClick={() => setDeleteId(editId)}
                                            disabled={loading}
                                        >
                                            <Trash2 className="h-4 w-4"/>
                                        </Button>
                                    </div>
                                </form>
                            )}
                        </TabsContent>
                    </Tabs>
                </DialogContent>
            </Dialog>
        </>
    );
}
