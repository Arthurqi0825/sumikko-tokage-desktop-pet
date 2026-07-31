import AppKit

enum SpriteAtlasError: LocalizedError {
    case missingResource
    case unreadableImage(URL)
    case invalidDimensions(actual: NSSize)
    case frameCreationFailed(row: Int, column: Int)

    var errorDescription: String? {
        switch self {
        case .missingResource:
            return "The native app bundle does not contain spritesheet.webp."
        case let .unreadableImage(url):
            return "Unable to decode sprite atlas at \(url.path)."
        case let .invalidDimensions(actual):
            return "Sprite atlas must be 1536x2288; received \(Int(actual.width))x\(Int(actual.height))."
        case let .frameCreationFailed(row, column):
            return "Unable to render sprite cell row \(row), column \(column)."
        }
    }
}

struct SpriteFrame {
    let image: NSImage
    let bitmap: NSBitmapImageRep
}

final class SpriteAtlas {
    let image: NSImage
    let pixelSize: NSSize
    private var frameCache: [Int: SpriteFrame] = [:]

    convenience init(bundle: Bundle = .main) throws {
        guard let url = bundle.url(forResource: "spritesheet", withExtension: "webp") else {
            throw SpriteAtlasError.missingResource
        }
        try self.init(url: url)
    }

    init(url: URL) throws {
        guard let source = NSImage(contentsOf: url) else {
            throw SpriteAtlasError.unreadableImage(url)
        }
        let width = source.representations.map(\.pixelsWide).max() ?? Int(source.size.width)
        let height = source.representations.map(\.pixelsHigh).max() ?? Int(source.size.height)
        pixelSize = NSSize(width: width, height: height)
        guard width == PetConstants.cellWidth * PetConstants.atlasColumns,
              height == PetConstants.cellHeight * PetConstants.atlasRows else {
            throw SpriteAtlasError.invalidDimensions(actual: pixelSize)
        }
        source.size = pixelSize
        image = source
    }

    func frame(row: Int, column: Int) throws -> SpriteFrame {
        let safeRow = clamp(row, minimum: 0, maximum: PetConstants.atlasRows - 1)
        let safeColumn = clamp(column, minimum: 0, maximum: PetConstants.atlasColumns - 1)
        let key = safeRow * PetConstants.atlasColumns + safeColumn
        if let cached = frameCache[key] {
            return cached
        }

        guard let bitmap = NSBitmapImageRep(
            bitmapDataPlanes: nil,
            pixelsWide: PetConstants.cellWidth,
            pixelsHigh: PetConstants.cellHeight,
            bitsPerSample: 8,
            samplesPerPixel: 4,
            hasAlpha: true,
            isPlanar: false,
            colorSpaceName: .deviceRGB,
            bytesPerRow: 0,
            bitsPerPixel: 0
        ), let graphicsContext = NSGraphicsContext(bitmapImageRep: bitmap) else {
            throw SpriteAtlasError.frameCreationFailed(row: safeRow, column: safeColumn)
        }

        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = graphicsContext
        graphicsContext.imageInterpolation = .high
        graphicsContext.cgContext.clear(
            CGRect(x: 0, y: 0, width: PetConstants.cellWidth, height: PetConstants.cellHeight)
        )
        let sourceRect = NSRect(
            x: safeColumn * PetConstants.cellWidth,
            y: Int(pixelSize.height) - ((safeRow + 1) * PetConstants.cellHeight),
            width: PetConstants.cellWidth,
            height: PetConstants.cellHeight
        )
        image.draw(
            in: NSRect(x: 0, y: 0, width: PetConstants.cellWidth, height: PetConstants.cellHeight),
            from: sourceRect,
            operation: .copy,
            fraction: 1,
            respectFlipped: false,
            hints: [.interpolation: NSImageInterpolation.high.rawValue]
        )
        graphicsContext.flushGraphics()
        NSGraphicsContext.restoreGraphicsState()

        let frameImage = NSImage(size: NSSize(width: PetConstants.cellWidth, height: PetConstants.cellHeight))
        frameImage.addRepresentation(bitmap)
        let frame = SpriteFrame(image: frameImage, bitmap: bitmap)
        frameCache[key] = frame
        return frame
    }
}
