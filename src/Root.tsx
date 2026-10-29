import React from 'react';
import { Composition } from 'remotion';
import { CompareVideo } from './CompareVideo';
import { defaultProps } from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CompareVideo"
        component={CompareVideo}
        durationInFrames={Math.round(defaultProps.durationInSeconds * 30)}
        fps={30}
        width={720}
        height={1280}
        defaultProps={defaultProps}
        calculateMetadata={({ props }) => {
          return {
            durationInFrames: Math.round((props.durationInSeconds || 7) * 30),
            props,
          };
        }}
      />
    </>
  );
};
