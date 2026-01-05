'use client';

import React, { useRef } from 'react';
import { IChartApi, MouseEventParams, Time, ISeriesApi } from 'lightweight-charts';

interface ChartContainerProps {
  children: React.ReactNode;
}

// Context approach or simple ref passing?
// Simple cloning of children with registration callbacks is often cleaner than Context for high-perf chart sync
// ensuring we don't re-render everything constantly.

// Interface for stored chart info
interface ChartRegistryEntry {
    chart: IChartApi;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    syncSeries?: ISeriesApi<any>;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({ children }) => {
  const registryRef = useRef<ChartRegistryEntry[]>([]);
  
  // Function for children to register themselves
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const registerChart = (chart: IChartApi, syncSeries?: ISeriesApi<any>) => {
    if (!registryRef.current.find(e => e.chart === chart)) {
      registryRef.current.push({ chart, syncSeries });
      setupSync(chart);
    } else {
        const entry = registryRef.current.find(e => e.chart === chart);
        if (entry && syncSeries) entry.syncSeries = syncSeries;
    }

    return () => {
        registryRef.current = registryRef.current.filter(e => e.chart !== chart);
    };
  };

  const setupSync = (chart: IChartApi) => {
      // Sync Time Scale
      const timeScale = chart.timeScale();
      
      timeScale.subscribeVisibleLogicalRangeChange((range) => {
          if (!range) return;
          registryRef.current.forEach(e => {
              if (e.chart !== chart) {
                  // Safety check for destroyed chart
                  try {
                       const otherTimeScale = e.chart.timeScale();
                       const otherRange = otherTimeScale.getVisibleLogicalRange();
                       if (!otherRange || otherRange.from !== range.from || otherRange.to !== range.to) {
                            e.chart.timeScale().setVisibleLogicalRange(range);
                       }
                  } catch (err) {
                      console.warn('[ChartContainer] Sync error (TimeScale), removing stale chart', err);
                      registryRef.current = registryRef.current.filter(r => r.chart !== e.chart);
                  }
              }
          });
      });
      
      chart.subscribeCrosshairMove((param: MouseEventParams) => {
          if (!param.point || !param.time) {
               registryRef.current.forEach(e => {
                   if (e.chart !== chart) {
                       try { e.chart.clearCrosshairPosition(); } catch(err) {/* ignore */}
                   }
               });
               return;
          }
          
          registryRef.current.forEach(e => {
               if (e.chart !== chart && e.syncSeries) {
                   try {
                       e.chart.setCrosshairPosition(NaN, param.time as Time, e.syncSeries);
                   } catch (err) {
                       console.warn('[ChartContainer] Sync error (Crosshair), removing stale chart', err);
                       registryRef.current = registryRef.current.filter(r => r.chart !== e.chart);
                   }
               }
          });
      });
  };

  return (
    <ChartSyncContext.Provider value={registerChart}>
      <div className="flex flex-col gap-[2px] bg-transparent w-full h-full">
        {children}
      </div>
    </ChartSyncContext.Provider>
  );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const ChartSyncContext = React.createContext<(chart: IChartApi, syncSeries?: ISeriesApi<any>) => (() => void) | void>(() => {});

export const useChartSync = () => React.useContext(ChartSyncContext);

