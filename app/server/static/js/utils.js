
export const transformAnnotation = (a) => {
    const { id, label, prob } = a
    if (a.additional_data) {
      try {
        const data = JSON.parse(a.additional_data)
        const { start_offset, end_offset } = data
        return {
          start_offset,
          end_offset,
          id,
          label,
          prob
        }
      } catch (e) {
        return {
          id,
          label,
          prob
        }
      }
    }
  }
  
  const nextNode = (node) => {
    if (node.hasChildNodes()) {
        return node.firstChild;
    } else {
        while (node && !node.nextSibling) {
            node = node.parentNode;
        }
        if (!node) {
            return null;
        }
        return node.nextSibling;
    }
  }
  
 export const getRangeSelectedNodes = (range) => {
    var node = range.startContainer;
    var endNode = range.endContainer;
  
    // Special case for a range that is contained within a single node
    if (node == endNode) {
        return [node];
    }
  
    // Iterate nodes until we hit the end container
    var rangeNodes = [];
    while (node && node != endNode) {
        rangeNodes.push( node = nextNode(node) );
    }
  
    // Add partially selected nodes at the start of the range
    node = range.startContainer;
    while (node && node != range.commonAncestorContainer) {
        rangeNodes.unshift(node);
        node = node.parentNode;
    }
  
    return rangeNodes;
  }

  export const uuidv4 = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  export const inRange = (number, rangeStart, rangeEnd) => {
    return number >= rangeStart && number <= rangeEnd
  }