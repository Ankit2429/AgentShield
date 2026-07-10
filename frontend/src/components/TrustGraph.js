import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function TrustGraph() {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;
    
    // Clear previous elements
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 300;
    const height = 200;

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    const nodes = [
      { id: "Agent A", group: 1, trust: 0.95 },
      { id: "Agent B", group: 2, trust: 0.85 }
    ];

    const links = [
      { source: "Agent A", target: "Agent B", value: 1 }
    ];

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-150))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
      .attr("stroke", "#334155")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 2);

    const node = svg.append("g")
      .attr("stroke", "#1e293b")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 12)
      .attr("fill", d => d.trust > 0.9 ? "#10b981" : "#f59e0b")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node.append("title").text(d => d.id);

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  }, []);

  return (
    <div className="p-6 bg-slate-900/50 rounded-2xl border border-slate-800 backdrop-blur-md">
      <h2 className="text-xl font-semibold text-violet-400 mb-2">Trust Topology Map</h2>
      <div className="flex justify-center items-center bg-slate-950/40 rounded-xl mt-4 border border-slate-850 p-2">
        <svg ref={svgRef}></svg>
      </div>
    </div>
  );
}
