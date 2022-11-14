import Foundation

public struct Queue<T> {
    private var data = [T]()
    private var head = 0
    public var count: Int {
        data.count
    }
    public var capacity: Int {
        get {
            return data.capacity
        }
        set {
            data.reserveCapacity(newValue)
        }
    }
    init() {}
    mutating func enqueue(_ element: T) {
        data.append(element)
    }
    mutating func dequeue() -> T? {
        data.removeFirst()
    }
//    mutating func dequeue() -> T? {// change data optional
//        guard head <= data.count, let element = data[head] else { return nil }
//        data[head] = nil
//        head += 1
//       
//        if head > data.count / 4 {
//            data.removeFirst(head)
//            head = 0
//        }
//        return element
//    }
    func peek() -> T? {
        data.first
    }
    func isFull() -> Bool {
        count == self.capacity
    }
    func isEmpty() -> Bool {
        data.isEmpty
    }
}

extension Queue: CustomStringConvertible,
                 CustomDebugStringConvertible,
                 ExpressibleByArrayLiteral,
                 Sequence{
    public var description: String {
        data.description
    }
    public var debugDescription: String {
        data.debugDescription
    }
    public init(arrayLiteral elements: T...) {
        self.init()
        elements.forEach { enqueue($0) }
    }
    public func makeIterator() -> some IteratorProtocol {
        AnyIterator(IndexingIterator(_elements: self.data.lazy))
    }
}

var myQueue: Queue = [1, 2]
for i in myQueue {
    print(i)
}