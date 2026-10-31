import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Loop,
  Audio,
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
  const activeItems = items.slice(0, is2Split ? 2 : 4);

  // Safe audio item
  const validAudioIdx = (audioIndex >= 0 && audioIndex < activeItems.length) ? audioIndex : 0;
  const audioItem = activeItems[validAudioIdx];
  const audioStartFrom = Math.round((audioItem?.startOffset || 0) * fps);
  const isAudioItemVideo = audioItem && !audioItem.videoSrc.match(/\.(jpg|jpeg|png|webp)$/i);

  // Title animation: popup at start, fade out at end
  const titleDurationFrames = titleDuration > 0 ? titleDuration * fps : Infinity;
  const showTitle = frame < titleDurationFrames;

  // Popup spring (0 to 1 scale)
  const popupScale = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.5, stiffness: 200 },
  });

  // Fade out during last 8 frames of title display
  const titleOpacity = interpolate(
    frame,
    [titleDurationFrames - 8, titleDurationFrames],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Names fade in right after title disappears
  const namesOpacity = interpolate(
    frame,
    [titleDurationFrames, titleDurationFrames + 8],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const showNames = frame >= titleDurationFrames;

  // Calculate dynamic font size based on text length to ensure 1 line per title
  const calcTitleSize = (text: string, baseRatio: number) => {
    const len = text ? text.length : 1;
    const scaleFactor = len > 8 ? Math.max(0.65, 8 / len) : 1.0;
    return Math.round(width * baseRatio * (titleFontSize || 1.0) * scaleFactor);
  };

  const titlePx = calcTitleSize(title, 0.075);
  const subtitlePx = calcTitleSize(subtitle, 0.088);
  const titleStrokePx = Math.round(titleStrokeWidth || 8);
  const namePx = Math.round(width * 0.052 * (nameFontSize || 1.0));
  const nameStrokePx = Math.round(nameStrokeWidth || 8);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {/* Google Fonts */}
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
        {activeItems.map((item: VideoItemConfig, idx: number) => {
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
              {/* Media Element (Image or Video) - Video volume is muted here */}
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
                <Loop durationInFrames={Math.max(1, Math.round((item.duration || 999) * fps))}>
                  <OffthreadVideo
                    src={staticFile(item.videoSrc)}
                    startFrom={startFrom}
                    volume={0}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                    }}
                  />
                </Loop>
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
                      fontSize: `${namePx}px`,
                      fontWeight: 900,
                      letterSpacing: '1px',
                      WebkitTextStroke: `${nameStrokePx}px ${nameStrokeColor}`,
                      paintOrder: 'stroke fill',
                      textShadow: `0 0 10px ${nameStrokeColor}, 0 4px 8px rgba(0, 0, 0, 0.8)`,
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

      {/* Explicit Audio Track from the selected audio source */}
      {isAudioItemVideo && (
        <Audio
          src={staticFile(audioItem.videoSrc)}
          startFrom={audioStartFrom}
          volume={1}
        />
      )}

      {/* Center Hook Title Overlay (Clean 2 lines) */}
      {showTitle && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${popupScale})`,
            opacity: titleOpacity,
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            fontFamily,
            pointerEvents: 'none',
            width: '90%',
          }}
        >
          {title && (
            <div
              style={{
                color: titleColor,
                fontSize: `${titlePx}px`,
                fontWeight: 900,
                letterSpacing: '1px',
                WebkitTextStroke: `${titleStrokePx}px ${titleStrokeColor}`,
                paintOrder: 'stroke fill',
                textShadow: `0 0 14px ${titleStrokeColor}, 0 6px 12px rgba(0, 0, 0, 0.7)`,
                lineHeight: 1.25,
                whiteSpace: 'nowrap',
              }}
            >
              {title}
            </div>
          )}
          {subtitle && (
            <div
              style={{
                color: titleColor,
                fontSize: `${subtitlePx}px`,
                fontWeight: 900,
                letterSpacing: '1px',
                WebkitTextStroke: `${titleStrokePx}px ${titleStrokeColor}`,
                paintOrder: 'stroke fill',
                textShadow: `0 0 14px ${titleStrokeColor}, 0 6px 12px rgba(0, 0, 0, 0.7)`,
                lineHeight: 1.25,
                marginTop: '4px',
                whiteSpace: 'nowrap',
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
