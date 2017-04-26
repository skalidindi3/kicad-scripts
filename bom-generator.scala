object KicadSchematic {
    // TODO: add field name vals?
    val requiredFieldsForBOM = Set("Manufacturer", "Manufacturer Part Number", "Supplier", "Supplier Part Number")

    object Component {
        val IDField = "L [^ ]* (.*)".r
        val NamedField = """F [0-9]* "(.*)" [HV] [0-9]* [0-9]* [0-9]*  [0-9]* C CNN "(.*)"""".r
        val NumberedField = """F ([0-9]*) "(.*)" [HV] [0-9]* [0-9]* [0-9]*  [0-9]* C CNN""".r

        def apply(raw: List[String]) = {
            val fields = (raw.flatMap{
                case IDField(value) => Some("Name" -> value)
                case NamedField(value, fieldName) => Some(fieldName -> value)
                case NumberedField("2", value) => Some("Footprint" -> value)
                case NumberedField("3", value) => Some("Datasheet" -> value)
                case _ => None
            }).toMap

            val name = fields("Name")
            val manu = fields("Manufacturer")
            val manuPN = fields("Manufacturer Part Number")
            val supplier = fields("Supplier")
            val supplierPN = fields("Supplier Part Number")
            val datasheet = fields.get("Datasheet")
            val footprint = fields.get("Footprint")

            // TODO: validate against known suppliers: Digi-Key
            new Component(name, manu, manuPN, supplier, supplierPN, datasheet, footprint)
        }
    }
    case class Component(name: String,
                         manufacturer: String,
                         manufacturerPN: String,
                         supplier: String,
                         supplierPN: String,
                         datasheet: Option[String],
                         footprint: Option[String])

    def componentMap(name: String, verbose: Boolean = false): Map[String, Component] = {
        componentList(name, verbose).map(c => c.name -> c).toMap
    }
    def componentList(infile: String, verbose: Boolean = false): List[Component] = {
        val lines = scala.io.Source.fromFile(infile).getLines.toList
        val linesWithIndex = lines.zipWithIndex
        val comps = for ((line, i) <- linesWithIndex if line == "$Comp") yield { i + 1 }
        val endcomps = for ((line, i) <- linesWithIndex if line == "$EndComp") yield i
        val allComponents = for ((start, end) <- comps.zip(endcomps)) yield { lines.slice(start, end) }

        def isValidComponent(raw: List[String]): Boolean = {
            val valid = requiredFieldsForBOM.forall(field => raw.exists(_.endsWith(s""""$field"""")))
            if (!valid && verbose) {
                println("Skipping component %s".format(raw.filter(_.startsWith("L ")).head.split(" ").last))
            }
            valid
        }

        val components = allComponents.filter(isValidComponent(_)).map(Component(_))
        if (verbose) {
            println(s"Found ${components.size} components")
        }

        components
    }

    object BillOfMaterials {
        def apply(infile: String) = new BillOfMaterials(componentList(infile))
    }
    class BillOfMaterials(components: List[Component]) {
        def printTabular(grid: Seq[Seq[String]], padding: Int): Unit = {
            val maxLengthPerField = grid.transpose.map(_.map(_.size).reduce(Math.max))
            for (line <- grid) {
                val formatted = for ((field, maxLength) <- line.zip(maxLengthPerField)) yield {
                    field + " " * (maxLength - field.size + padding)
                }
                println(formatted.mkString)
            }
        }

        def csv(volume: Int = 1): Seq[String] = {
            val header = "Manufacturer,Manufacturer Part Number,Supplier,Supplier Part Number,Quantity,Designator"
            val partMap = components.groupBy(c => c.supplier + " " + c.supplierPN)
            val csvBody = for ((_, commonPartList) <- partMap) yield {
                val c = commonPartList.head
                val quantity = commonPartList.size * volume
                val designator = commonPartList.map(_.name).mkString(" ")
                val info = List(c.manufacturer, c.manufacturerPN, c.supplier, c.supplierPN, quantity, designator)
                info.mkString(",")
            }
            header +: csvBody.toList.sorted
        }
        def show(volume: Int = 1, padding: Int = 2): Unit = printTabular(csv(volume).map(_.split(",").toSeq), padding)

        def digikeyCsv(volume: Int = 1): Seq[String] = {
            val digikeyHeader = "Digi-Key Part Number,Customer Reference,Quantity"
            val partMap = components.filter(_.supplier == "Digi-Key").groupBy(_.supplierPN)
            val csvBody = for ((partNumber, commonPartList) <- partMap) yield {
                val c = commonPartList.head
                val quantity = commonPartList.size * volume
                val designator = commonPartList.map(_.name).mkString(" ")
                val info = List(partNumber, designator, quantity)
                info.mkString(",")
            }
            digikeyHeader +: csvBody.toList.sorted
        }
        def digikeyShow(volume: Int = 1, padding: Int = 2): Unit = printTabular(digikeyCsv(volume).map(_.split(",").toSeq), padding)

        //def save(outfile: String)
    }
}
