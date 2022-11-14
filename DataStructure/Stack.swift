import Foundation
public struct Stack<T> {
    private var elements = [T]()
    public var count: Int {
        elements.count
    }
    init() {}
    mutating func pop() -> T? {
        self.elements.popLast()
    }
    mutating func push(_ element: T) {
        self.elements.append(element)
    }
    func peek() -> T? {
        self.elements.last
    }
    func isEmpty() -> Bool {
        self.elements.isEmpty
    }
}
//public struct ArrayIterator<T>: IteratorProtocol {
//    var currentElement: [T]
//    init(elements: [T]) {
//        self.currentElement = elements
//    }
//   
//    mutating public func next() -> T? {
//        if (self.currentElement.isEmpty == false) {
//            return self.currentElement.popLast()
//        }
//        return nil
//    }
//}
extension Stack: CustomStringConvertible,
                 CustomDebugStringConvertible,
                 ExpressibleByArrayLiteral,
                 Sequence{
    public var description: String {
        return "description: " + self.elements.description
    }
    public var debugDescription: String {
        return "debugDescription" + self.elements.debugDescription
    }
    public init(arrayLiteral elements: T...) {
        self.init()
        elements.forEach { push($0) }
    }
//    public func makeIterator() -> some IteratorProtocol {
//        return ArrayIterator<T>(elements: self.elements)
//    }
    public func makeIterator() -> some IteratorProtocol {
        return AnyIterator(IndexingIterator(_elements: self.elements.lazy.reversed()))
    }
}
var myStack: Stack<Int> = [5, 4, 3, 2, 1]
for i in myStack {
    print(i)
}

