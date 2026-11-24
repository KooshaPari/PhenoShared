// Phinbox — DetailView Field Rendering

import SwiftUI

// MARK: - Field Body

extension DetailView {
    @ViewBuilder
    var fieldBody: some View {
        switch request.spec.field {
        case .boolean(_, _):
            Toggle(isOn: $boolVal) {
                Text(boolVal ? "Yes" : "No").foregroundStyle(.white)
            }
            .toggleStyle(.switch).tint(Color.teal)

        case .choice(_, let opts, _):
            choiceList(opts)

        case .text(_, _, let placeholder, let maxLen, let secret, _):
            if secret == true {
                secretField(placeholder: placeholder ?? "Enter answer...")
            } else {
                fieldInput(placeholder: placeholder ?? "Enter answer...",
                           binding: $textVal, multiline: false, maxLength: maxLen)
            }

        case .longText(_, _, let maxLen):
            fieldInput(placeholder: "Enter answer...",
                       binding: $textVal, multiline: true, maxLength: maxLen)

        case .integer(_, _, _, _):
            fieldInput(placeholder: "Enter number...",
                       binding: $intVal, multiline: false, maxLength: nil)

        case .dateTime(_, _, let pickerKind):
            datePicker(kind: pickerKind)

        case .unknown(_, let kind):
            Text("Unsupported field type: \(kind)")
                .foregroundStyle(.white.opacity(0.5))
        }
    }
}

// MARK: - Form Card

extension DetailView {
    var formCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(request.spec.field.labelText)
                .font(.headline).foregroundStyle(.white)
            fieldBody
        }
        .padding(24).background(glass)
    }
}

// MARK: - Secret Field

extension DetailView {
    private func secretField(placeholder: String) -> some View {
        SecureField(placeholder, text: $textVal)
            .textFieldStyle(.plain).padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Color.white.opacity(0.04))
                    .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(Color.white.opacity(0.1)))
            )
    }
}

// MARK: - Date Picker

extension DetailView {
    @ViewBuilder
    func datePicker(kind: String?) -> some View {
        let kind = kind ?? "datetime"
        switch kind {
        case "date":
            DatePicker("Date", selection: $dateVal, displayedComponents: .date)
                .datePickerStyle(.compact).tint(Color.teal)
        case "time":
            DatePicker("Time", selection: $dateVal, displayedComponents: .hourAndMinute)
                .datePickerStyle(.compact).tint(Color.teal)
        case "datetime", "composite", _:
            DatePicker("Date & time", selection: $dateVal, displayedComponents: [.date, .hourAndMinute])
                .datePickerStyle(.compact).tint(Color.teal)
        }
    }

    func datePickerComponents(_ kind: String?) -> DatePickerComponents {
        switch kind {
        case "date":  return [.date]
        case "time":  return [.hourAndMinute]
        default:      return [.date, .hourAndMinute]
        }
    }
}

// MARK: - Choice List

extension DetailView {
    func choiceList(_ opts: [ChoiceOption]) -> some View {
        VStack(spacing: 10) {
            ForEach(opts, id: \.value) { opt in choiceRow(opt) }
        }
    }

    private func choiceRow(_ opt: ChoiceOption) -> some View {
        Button { withAnimation { choice = opt.value } } label: {
            HStack(spacing: 12) {
                Circle().fill(choice == opt.value ? Color.teal : Color.clear)
                    .frame(width: 18, height: 18)
                    .overlay(Circle().strokeBorder(
                        choice == opt.value ? Color.teal : Color.white.opacity(0.3), lineWidth: 2))
                VStack(alignment: .leading, spacing: 2) {
                    Text(opt.label).foregroundStyle(.white)
                    if let d = opt.description {
                        Text(d).font(.caption).foregroundStyle(.white.opacity(0.5))
                    }
                }
                Spacer()
                if choice == opt.value {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.teal)
                }
            }
            .padding(14)
            .background(choiceBg(selected: choice == opt.value))
        }
        .buttonStyle(.plain)
    }

    private func choiceBg(selected: Bool) -> some View {
        RoundedRectangle(cornerRadius: 10, style: .continuous)
            .fill(selected ? Color.teal.opacity(0.12) : Color.white.opacity(0.04))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(selected ? Color.teal.opacity(0.4) : Color.white.opacity(0.08)))
    }
}
