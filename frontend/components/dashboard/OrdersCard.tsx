'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, XCircle, Ban } from 'lucide-react';
import { getPendingOrders, cancelOrder, cancelAllOrders, OrderResponse } from '@/lib/api/execution';
import { logger } from '@/lib/api/app-logger';

interface OrdersCardProps {
  accountId?: string;
  onRefresh?: () => void;
}

export const OrdersCard: React.FC<OrdersCardProps> = ({ accountId, onRefresh }) => {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancellingAll, setCancellingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = async () => {
    if (!accountId) return;
    try {
      setLoading(true);
      const data = await getPendingOrders(accountId);
      setOrders(data);
      setError(null);
    } catch (err) {
      logger.error('Failed to fetch orders:', err);
      // Fail gracefully for now
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [accountId]);

  const handleCancel = async (orderId: string) => {
    setCancellingId(orderId);
    try {
      await cancelOrder(orderId);
      setOrders(prev => prev.filter(o => o.id !== orderId));
      if (onRefresh) onRefresh();
    } catch (err) {
      logger.error('Failed to cancel order:', err);
      alert('Failed to cancel order.');
    } finally {
      setCancellingId(null);
    }
  };

  const handleCancelAll = async () => {
     if (!accountId) return;
     if (!confirm("Cancel ALL pending orders?")) return;
     
     setCancellingAll(true);
     try {
         const res = await cancelAllOrders(accountId);
         if (res.errors && res.errors.length > 0) {
             alert(`Cancelled ${res.cancelled} orders with errors: \n${res.errors.join('\n')}`);
         }
         await fetchOrders();
         if (onRefresh) onRefresh();
     } catch (err) {
         logger.error('Failed to cancel all orders:', err);
         alert('Failed to cancel all orders.');
     } finally {
         setCancellingAll(false);
     }
  };

  if (!accountId) return null;

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-gray-100">Pending Orders</h2>
            {orders.length > 0 && <span className="text-sm text-gray-400">({orders.length})</span>}
        </div>
        <div className="flex items-center gap-2">
            {orders.length > 0 && (
                <Button 
                    variant="destructive" 
                    size="sm" 
                    onClick={handleCancelAll} 
                    disabled={loading || cancellingAll}
                    className="bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-500/20"
                >
                    {cancellingAll ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Ban className="w-4 h-4 mr-1" />}
                    Cancel All
                </Button>
            )}
            <Button variant="ghost" size="sm" onClick={fetchOrders} disabled={loading}>
                Refresh
            </Button>
        </div>
      </div>

       {loading && orders.length === 0 ? (
        <div className="h-32 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-8 text-gray-500 text-sm">
          No pending orders.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-xs">
                <th className="text-left py-2 px-4">ID</th>
                <th className="text-left py-2 px-4">Instrument</th>
                <th className="text-right py-2 px-4">Units</th>
                <th className="text-right py-2 px-4">Price</th>
                <th className="text-right py-2 px-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-800/20">
                  <td className="py-2 px-4 font-mono text-gray-300">{order.id}</td>
                  <td className="py-2 px-4 font-medium text-gray-200">{order.instrument}</td>
                  <td className="py-2 px-4 text-right font-mono text-gray-400">{order.units}</td>
                  <td className="py-2 px-4 text-right font-mono text-gray-300">{order.price}</td>
                  <td className="py-2 px-4 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-400 hover:text-red-300 hover:bg-red-400/10 h-8"
                      onClick={() => handleCancel(order.id)}
                      disabled={cancellingId === order.id}
                    >
                      {cancellingId === order.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-4 h-4" />}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
