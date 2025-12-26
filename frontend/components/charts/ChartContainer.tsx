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
        // Update series if needed (e.g. indicator type change)
        const entry = registryRef.current.find(e => e.chart === chart);
        if (entry && syncSeries) entry.syncSeries = syncSeries;
    }
  };

  const setupSync = (chart: IChartApi) => {
      // Sync Time Scale
      const timeScale = chart.timeScale();
      
      timeScale.subscribeVisibleLogicalRangeChange((range) => {
          if (!range) return;
          registryRef.current.forEach(e => {
              if (e.chart !== chart) {
                  const otherTimeScale = e.chart.timeScale();
                  const otherRange = otherTimeScale.getVisibleLogicalRange();
                  if (!otherRange || otherRange.from !== range.from || otherRange.to !== range.to) {
                       e.chart.timeScale().setVisibleLogicalRange(range);
                  }
              }
          });
      });
      
      chart.subscribeCrosshairMove((param: MouseEventParams) => {
          if (!param.point || !param.time) {
               registryRef.current.forEach(e => {
                   if (e.chart !== chart) e.chart.clearCrosshairPosition();
               });
               return;
          }
          
          registryRef.current.forEach(e => {
               if (e.chart !== chart && e.syncSeries) {
                   e.chart.setCrosshairPosition(NaN, param.time as Time, e.syncSeries);
               }
          });
      });
  };

  return (
    <ChartSyncContext.Provider value={registerChart}>
      <div className="flex flex-col gap-[2px] bg-transparent w-full">
        {children}
      </div>
    </ChartSyncContext.Provider>
  );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const ChartSyncContext = React.createContext<(chart: IChartApi, syncSeries?: ISeriesApi<any>) => void>(() => {});

export const useChartSync = () => React.useContext(ChartSyncContext);
