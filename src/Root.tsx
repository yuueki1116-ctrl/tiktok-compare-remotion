import React from 'react';
import { Composition } from 'remotion';
import { CompareVideo } from './CompareVideo';
import { defaultProps, CompareVideoProps } from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CompareVideo"
        component={CompareVideo as unknown as React.FC<Record<string, unknown>>}
        durationInFrames={Math.round(defaultProps.durationInSeconds * 30)}
        fps={30}
        width={720}
        height={1280}
        defaultProps={defaultProps as unknown as Record<string, unknown>}
        calculateMetadata={({ props }) => {
          const p = props as unknown as CompareVideoProps;
          return {
            durationInFrames: Math.round((p.durationInSeconds || 7) * 30),
            props,
          };
        }}
      />
    </>
  );
};
