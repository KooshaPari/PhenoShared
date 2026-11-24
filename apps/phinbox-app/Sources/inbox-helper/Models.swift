// Phinbox — Data Models

import Foundation

struct Origin: Decodable, Hashable {
    let hostname: String
    let process: String
    let pid: UInt32
}

struct ChoiceOption: Decodable, Hashable {
    let value: String
    let label: String
    let description: String?
}

struct ButtonSpec: Decodable, Hashable {
    let cancel: String
    let confirm: String
    let default_is_cancel: Bool?
}

enum FieldSpec: Decodable, Hashable {
    case text(label: String, defaultValue: String?, placeholder: String?, maxLength: Int?, secret: Bool?, pattern: String?)
    case longText(label: String, defaultValue: String?, maxLength: Int?)
    case integer(label: String, min: Int?, max: Int?, defaultValue: Int?)
    case choice(label: String, options: [ChoiceOption], defaultIndex: Int?)
    case boolean(label: String, defaultValue: Bool?)
    case dateTime(label: String, defaultValue: String?, pickerKind: String?)
    case unknown(label: String, kind: String)

    enum CodingKeys: String, CodingKey {
        case kind, label, options, placeholder, max_length, secret, pattern
        case default_value, default_index, min, max, picker_kind
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try c.decode(String.self, forKey: .kind)
        let label = try c.decode(String.self, forKey: .label)
        switch kind {
        case "text":
            self = .text(label: label,
                         defaultValue: try c.decodeIfPresent(String.self, forKey: .default_value),
                         placeholder: try c.decodeIfPresent(String.self, forKey: .placeholder),
                         maxLength: try c.decodeIfPresent(Int.self, forKey: .max_length),
                         secret: try c.decodeIfPresent(Bool.self, forKey: .secret),
                         pattern: try c.decodeIfPresent(String.self, forKey: .pattern))
        case "long_text":
            self = .longText(label: label,
                             defaultValue: try c.decodeIfPresent(String.self, forKey: .default_value),
                             maxLength: try c.decodeIfPresent(Int.self, forKey: .max_length))
        case "integer":
            self = .integer(label: label,
                            min: try c.decodeIfPresent(Int.self, forKey: .min),
                            max: try c.decodeIfPresent(Int.self, forKey: .max),
                            defaultValue: try c.decodeIfPresent(Int.self, forKey: .default_value))
        case "choice":
            let opts = try c.decode([ChoiceOption].self, forKey: .options)
            self = .choice(label: label, options: opts,
                           defaultIndex: try c.decodeIfPresent(Int.self, forKey: .default_index))
        case "bool":
            self = .boolean(label: label,
                            defaultValue: try c.decodeIfPresent(Bool.self, forKey: .default_value))
        case "date_time":
            self = .dateTime(label: label,
                             defaultValue: try c.decodeIfPresent(String.self, forKey: .default_value),
                             pickerKind: try c.decodeIfPresent(String.self, forKey: .picker_kind))
        case "secret":
            self = .text(label: label, defaultValue: nil, placeholder: nil,
                         maxLength: nil, secret: true, pattern: nil)
        default:
            self = .unknown(label: label, kind: kind)
        }
    }

    func encode(to encoder: Encoder) throws {
        fatalError("encode not implemented — client is decode-only")
    }

    // MARK: - Convenience accessors

    var labelText: String {
        switch self {
        case .text(let l, _, _, _, _, _), .longText(let l, _, _), .integer(let l, _, _, _),
             .choice(let l, _, _), .boolean(let l, _), .dateTime(let l, _, _), .unknown(let l, _):
            return l
        }
    }

    var kind: String {
        switch self {
        case .text:     return "text"
        case .longText: return "long_text"
        case .integer:  return "integer"
        case .choice:   return "choice"
        case .boolean:  return "bool"
        case .dateTime: return "date_time"
        case .unknown(_, let k): return k
        }
    }
}

struct NotesSpec: Decodable, Hashable {
    let label: String
    let required: Bool?
}

struct PromptSpec: Decodable, Hashable {
    let title: String
    let question: String
    let field: FieldSpec
    let notes: NotesSpec?
    let urgency: Urgency?
    let buttons: ButtonSpec?
}

struct PendingRequest: Decodable, Identifiable, Hashable {
    var id: String { request_id }
    let request_id: String
    let origin: Origin
    let spec: PromptSpec
    let queued_at_ms: UInt64
    let expires_at_ms: UInt64
    let state: String
    func hash(into hasher: inout Hasher) { hasher.combine(request_id) }
    static func == (lhs: Self, rhs: Self) -> Bool { lhs.request_id == rhs.request_id }
}

// MARK: - Urgency

enum Urgency: String, Decodable, Comparable {
    case error
    case warning
    case info
    case secret

    var sortOrder: Int {
        switch self {
        case .error:   return 0
        case .warning: return 1
        case .info:    return 2
        case .secret:  return 3
        }
    }

    static func < (lhs: Urgency, rhs: Urgency) -> Bool {
        lhs.sortOrder < rhs.sortOrder
    }
}
