import Foundation
struct Constants {
    static let defaultBufferCapacity = 16
}
enum CircularBufferOperation {
    case Ignore, Overwrite
}
struct CircularBuffer<T> {
    private var data: [T]
    private var head = 0, tail = 0
    private var internalCount = 0
    private var overwriteOperation = CircularBufferOperation.Overwrite
    var count: Int {
        return internalCount
    }
    var capacity: Int {
        get {
            return data.capacity
        }
        set {
            data.reserveCapacity(newValue)
        }
    }
    init() {
        data = [T]()
        data.reserveCapacity(Constants.defaultBufferCapacity)
    }
    init(_ count: Int, overwriteOperation: CircularBufferOperation = .Overwrite) {
        var capacity = count
        if capacity < 1 {
            capacity = Constants.defaultBufferCapacity
        }
        if (capacity & (~capacity + 1)) != capacity {
            var b = 1
            while (b < capacity) {
                b = b << 1
            }
            capacity = b
        }
        data = [T]()
        data.reserveCapacity(capacity)
        self.overwriteOperation = overwriteOperation
    }
    init<S: Sequence>(_ elements: S, size: Int) where S.Iterator.Element == T {
        self.init(size)
        elements.forEach({ push(element: $0) })
    }
    mutating func push(element: T) {
        if isFull() {
            switch(overwriteOperation) {
            case .Ignore: return
            case .Overwrite: pop()
            }
        }
        if data.endIndex < data.capacity {
            data.append(element)
        } else {
            data[tail] = element
        }
        tail = incrementPointer(pointer: tail)
        internalCount += 1
    }
    mutating func pop() -> T? {
        if isEmpty() {
            return nil
        }
        let ret = data[head]
        head = incrementPointer(pointer: head)
        internalCount -= 1
        return ret
    }
    func peek() -> T? {
        if isEmpty() {
            return nil
        }
        return data[head]
    }
    mutating func clear() {
        head = 0
        tail = 0
        internalCount = 0
        data.removeAll(keepingCapacity: true)
    }
    func isFull() -> Bool {
        return count == data.capacity
    }
    func isEmpty() -> Bool {
        return count == 0
    }
}