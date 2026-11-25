//! Apple Vision OCR backend for journey keyframe assertions.
//!
//! Gated behind the `vision` cargo feature and the
//! `PHENOTYPE_JOURNEY_OCR_BACKEND=vision` env var. When both are active and
//! the host is macOS, Vision's `VNRecognizeTextRequest` runs at
//! `.accurate` recognition level against each keyframe PNG and returns the
//! concatenated recognised text (newline-separated observations).
//!
//! Why: Catppuccin Mocha + JetBrains Mono confuses vanilla Tesseract
//! (digit '0' vs letter 'O' vs letter 'l' collapse). Apple Vision handles
//! anti-aliased terminal fonts far better and needs no ImageMagick
//! pre-processing pipeline.
//!
//! Library choice: `objc2` + `objc2-foundation` + `objc2-vision` — idiomatic
//! typed bindings, no hand-rolled `msg_send!`.

#![cfg(all(feature = "vision", target_os = "macos"))]

use crate::JourneyError;
use std::path::Path;

use objc2::rc::Retained;
use objc2::runtime::AnyObject;
use objc2::AnyThread;
use objc2_foundation::{NSArray, NSDictionary, NSString, NSURL};
use objc2_vision::{
    VNImageOption, VNImageRequestHandler, VNRecognizeTextRequest, VNRequest,
    VNRequestTextRecognitionLevel,
};

/// Run Apple Vision OCR against a single PNG keyframe.
///
/// Returns concatenated recognised text (one observation per line) on
/// success. Returns [`JourneyError::Ocr`] with a descriptive message on
/// any Vision or Foundation failure.
pub fn ocr_vision(frame_path: &Path) -> Result<String, JourneyError> {
    // Vision requires an absolute URL. Canonicalise relative paths so the
    // caller can pass either flavour.
    let canonical = if frame_path.is_absolute() {
        frame_path.to_path_buf()
    } else {
        frame_path
            .canonicalize()
            .map_err(|e| JourneyError::Ocr(format!("canonicalize {}: {e}", frame_path.display())))?
    };
    let path_str = canonical
        .to_str()
        .ok_or_else(|| JourneyError::Ocr(format!("non-utf8 path {}", canonical.display())))?;

    unsafe {
        let ns_path = NSString::from_str(path_str);
        let url: Retained<NSURL> = NSURL::fileURLWithPath(&ns_path);

        // Empty options dictionary — typed as NSDictionary<VNImageOption, AnyObject>.
        let empty_options: Retained<NSDictionary<VNImageOption, AnyObject>> =
            NSDictionary::new();

        let handler: Retained<VNImageRequestHandler> = VNImageRequestHandler::initWithURL_options(
            VNImageRequestHandler::alloc(),
            &url,
            &empty_options,
        );

        let request: Retained<VNRecognizeTextRequest> =
            VNRecognizeTextRequest::init(VNRecognizeTextRequest::alloc());
        request.setRecognitionLevel(VNRequestTextRecognitionLevel::Accurate);
        // Preserve `__EXIT_0__` sentinels and other identifier-shaped tokens.
        request.setUsesLanguageCorrection(false);

        // performRequests_error takes `&NSArray<VNRequest>`. Upcast our
        // concrete VNRecognizeTextRequest via the retained-slice constructor
        // after re-typing through a transparent Retained cast.
        let as_base: Retained<VNRequest> = Retained::cast_unchecked(request.clone());
        let req_array: Retained<NSArray<VNRequest>> =
            NSArray::from_retained_slice(&[as_base]);

        handler
            .performRequests_error(&req_array)
            .map_err(|e| JourneyError::Ocr(format!("VNImageRequestHandler failed: {:?}", e)))?;

        let results = request.results();
        let mut out = String::new();
        if let Some(results) = results {
            let count = results.count();
            for i in 0..count {
                let obs = results.objectAtIndex(i);
                let candidates = obs.topCandidates(1);
                if candidates.count() >= 1 {
                    let cand = candidates.objectAtIndex(0);
                    let s = cand.string();
                    out.push_str(&s.to_string());
                    out.push('\n');
                }
            }
        }
        Ok(out)
    }
}
