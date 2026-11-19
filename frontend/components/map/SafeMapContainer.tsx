"use client";

import {
  LeafletContext,
  createLeafletContext,
  type LeafletContextInterface,
} from "@react-leaflet/core";
import { Map as LeafletMap } from "leaflet";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

import type { FitBoundsOptions, LatLngBoundsExpression, MapOptions } from "leaflet";

export type SafeMapContainerProps = MapOptions & {
  bounds?: LatLngBoundsExpression;
  boundsOptions?: FitBoundsOptions;
  children?: ReactNode;
  className?: string;
  id?: string;
  placeholder?: ReactNode;
  style?: CSSProperties;
  whenReady?: () => void;
};

/**
 * Drop-in replacement for react-leaflet's `MapContainer`.
 *
 * The upstream component removes the Leaflet map synchronously in an effect
 * cleanup. React StrictMode (enabled by default in Next.js development) mounts,
 * unmounts and remounts the tree in the same commit, so the map gets removed
 * while its layer children are being re-attached to the same DOM node. The
 * result is `Cannot read properties of undefined (reading 'appendChild')` and
 * `Map container is being reused by another instance`.
 *
 * Here the removal is deferred to a macrotask. If the component is remounted
 * (StrictMode or fast refresh) inside the same task, the pending removal is
 * cancelled and the existing map instance is kept, so layers always talk to a
 * live map. A real unmount lets the timer fire and cleans everything up.
 */
export const SafeMapContainer = forwardRef<LeafletMap | null, SafeMapContainerProps>(
  function SafeMapContainer(
    {
      bounds,
      boundsOptions,
      center,
      children,
      className,
      id,
      placeholder,
      style,
      whenReady,
      zoom,
      ...options
    },
    forwardedRef,
  ) {
    const [staticProps] = useState({ className, id, style });
    const [context, setContext] = useState<LeafletContextInterface | null>(null);
    const mapInstanceRef = useRef<LeafletMap | undefined>(undefined);
    const containerRef = useRef<HTMLDivElement | null>(null);

    useImperativeHandle<LeafletMap | null, LeafletMap | null>(
      forwardedRef,
      () => context?.map ?? null,
      [context],
    );

    const mapRef = useCallback(
      (node: HTMLDivElement | null) => {
        if (node === null) {
          // React may detach refs during its StrictMode remount cycle. The
          // map is kept alive; the effect below only removes it when its
          // container has actually left the document.
          return;
        }
        containerRef.current = node;
        if (mapInstanceRef.current) {
          return;
        }
        const map = new LeafletMap(node, options);
        mapInstanceRef.current = map;
        if (center != null && zoom != null) {
          map.setView(center, zoom);
        } else if (bounds != null) {
          map.fitBounds(bounds, boundsOptions);
        }
        if (whenReady != null) {
          map.whenReady(whenReady);
        }
        setContext(createLeafletContext(map));
      },
      // map options are only read on first mount, matching react-leaflet.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [],
    );

    useEffect(() => {
      return () => {
        // StrictMode runs this cleanup while the DOM node is still mounted,
        // then re-runs the effect. Checking `isConnected` when the timer
        // fires distinguishes that simulated unmount from a real one, so the
        // map (and its panes) is never removed underneath the layer children.
        const map = mapInstanceRef.current;
        const node = containerRef.current;
        if (!map || !node) {
          return;
        }
        setTimeout(() => {
          if (!node.isConnected) {
            map.remove();
            if (mapInstanceRef.current === map) {
              mapInstanceRef.current = undefined;
            }
          }
        }, 0);
      };
    }, []);

    const contents = context
      ? <LeafletContext.Provider value={context}>{children}</LeafletContext.Provider>
      : (placeholder ?? null);

    return (
      <div {...staticProps} ref={mapRef}>
        {contents}
      </div>
    );
  },
);
