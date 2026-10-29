import React from 'react';
import {
  AbsoluteFill,
  Img,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { CompareVideoProps, VideoItemConfig } from './types';

export const CompareVideo: React.FC<CompareVideoProps> = ({
  title,
  subtitle,
  titleDuration = 1.5,
  titleColor = '#ffffff',
  titleStrokeColor = '#ff2d78',
  fontFamily = "'Mochiy Pop One', sans-serif",
  titleFontSize = 0.95,
  titleStrokeWidth = 8,
  nameColor = '#ffffff',
  nameStrokeColor = '#d6006e',
  nameFontFamily = "'M PLUS Rounded 1c', sans-serif",
  nameFontSize = 1.0,
  nameStrokeWidth = 8,
  items,
  layout,
  audioIndex = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Determine layout: 2-split (left/right) if items count is 2 or layout is '2-split'
  const is2Split = layout === '2-split' || items.length === 2;

  // Title animation: popup at start, fade out at end
  const titleDurationFrames = titleDuration > 0 ? titleDuration * fps : Infinity;
  const titleSpring = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 200, mass: 0.8 },
  });

  const fadeOutStart = Math.max(0, titleDurationFrames - 10);
  const titleOpacity = interpolate(
    frame,
    [0, 8, fadeOutStart, titleDurationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const showTitle = frame < titleDurationFrames;

  // Names animation: appear right as title finishes fading out
  const namesFadeInStart = titleDuration > 0 ? fadeOutStart : 0;
  const namesOpacity = interpolate(
    frame,
    [namesFadeInStart, namesFadeInStart + 12],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const showNames = frame >= namesFadeInStart;

  // Stroke and shadow style generator
  const createStrokeStyle = (strokeColor: string, strokeWidth: number) => ({
    WebkitTextStroke: `${strokeWidth}px ${strokeColor}`,
    paintOrder: 'stroke fill' as const,
    textShadow: `
      0 0 10px ${strokeColor},
      0 4px 8px rgba(0, 0, 0, 0.75)
    `,
  });

  // Calculate dynamic font size based on text length to ensure 1 line per title
  const calcTitleSize = (text: string, baseRatio: number) => {
    const len = text ? text.length : 1;
    const scaleFactor = len > 8 ? Math.max(0.65, 8 / len) : 1.0;
    return Math.round(width * baseRatio * (titleFontSize || 1.0) * scaleFactor);
  };

  const titleSizePx = calcTitleSize(title, 0.076);
  const subtitleSizePx = calcTitleSize(subtitle, 0.082);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#000000',
      }}
    >
      {/* Import Popular TikTok & Shorts Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=DotGothic16&family=Hachi+Maru+Pop&family=Kaisei+Tokumin:wght@700;800&family=Kiwi+Maru:wght@500;800&family=M+PLUS+Rounded+1c:wght@800;900&family=Mochiy+Pop+One&family=Noto+Sans+JP:wght@800;900&family=Potta+One&family=Reggae+One&family=RocknRoll+One&family=Zen+Maru+Gothic:wght@700;900&display=swap');
      `}</style>

      {/* Grid: 2 columns (1 row for 2-split, 2 rows for 4-grid) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gridTemplateRows: is2Split ? '1fr' : '1fr 1fr',
          width: '100%',
          height: '100%',
          gap: '3px',
          backgroundColor: '#000000',
        }}
      >
        {items.slice(0, is2Split ? 2 : 4).map((item: VideoItemConfig, idx: number) => {
          const isAudioSource = idx === audioIndex;
          const startFrom = Math.round((item.startOffset || 0) * fps);
          const isImage = item.videoSrc.match(/\.(jpg|jpeg|png|webp)$/i);

          return (
            <div
              key={idx}
              style={{
                position: 'relative',
                width: '100%',
                height: '100%',
                overflow: 'hidden',
                backgroundColor: '#111111',
              }}
            >
              {/* Media Element (Image or Video) */}
              {isImage ? (
                <Img
                  src={staticFile(item.videoSrc)}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />
              ) : (
                <Video
                  src={staticFile(item.videoSrc)}
                  startFrom={startFrom}
                  volume={isAudioSource ? 1 : 0}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />
              )}

              {/* Name Overlay */}
              {showNames && item.name && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: is2Split ? '60px' : '24px',
                    left: 0,
                    right: 0,
                    textAlign: 'center',
                    pointerEvents: 'none',
                    zIndex: 10,
                    opacity: namesOpacity,
                    transform: `scale(${interpolate(namesOpacity, [0, 1], [0.85, 1])})`,
                    fontFamily: nameFontFamily,
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      color: nameColor,
                      fontSize: `${Math.round(width * 0.056 * (nameFontSize || 1.0))}px`,
                      fontWeight: 900,
                      letterSpacing: '1px',
                      whiteSpace: 'nowrap',
                      ...createStrokeStyle(nameStrokeColor, nameStrokeWidth || 8),
                      transform: 'scale(1, 1.05)',
                    }}
                  >
                    {item.name}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Center Hook Title Overlay (Clean 2 lines) */}
      {showTitle && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${titleSpring})`,
            opacity: titleOpacity,
            textAlign: 'center',
            width: '96%',
            pointerEvents: 'none',
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            fontFamily: fontFamily,
          }}
        >
          {title && (
            <div
              style={{
                color: titleColor,
                fontSize: `${titleSizePx}px`,
                fontWeight: 900,
                letterSpacing: '1.5px',
                whiteSpace: 'nowrap',
                ...createStrokeStyle(titleStrokeColor, titleStrokeWidth || 8),
                transform: 'scale(1, 1.05)',
              }}
            >
              {title}
            </div>
          )}
          {subtitle && (
            <div
              style={{
                color: titleColor,
                fontSize: `${subtitleSizePx}px`,
                fontWeight: 900,
                letterSpacing: '1.5px',
                whiteSpace: 'nowrap',
                ...createStrokeStyle(titleStrokeColor, (titleStrokeWidth || 8) + 1),
                transform: 'scale(1, 1.05)',
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};
