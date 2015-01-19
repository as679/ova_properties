__author__ = 'asteer'

import sys
import tarfile
import xml.etree.ElementTree as elementtree

class OVA(object):
    namespace = {'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
                 'vmw': 'http://www.vmware.com/schema/ovf',
                 'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if 'network' not in self.__dict__:
            self.network = None

        if 'ova' in self.__dict__:
            self.ovf = elementtree.parse(self.extractovf(self.ova))
            self.networkProperty = self.parseNetworkSection(self.ovf.find('ovf:NetworkSection', OVA.namespace))
            self.virtualSystemProperties = []
            for tag in ('ovf:VirtualSystemCollection', './/ovf:VirtualSystem'):
                virtualSystems = self.ovf.findall(tag, OVA.namespace)
                if len(virtualSystems) > 0:
                    for virtualSystem in virtualSystems:
                        for property in self.parseVirtualSystem(virtualSystem):
                            self.virtualSystemProperties.append(property)

    def extractovf(self, ova):
        ovf = None
        if tarfile.is_tarfile(ova):
            tar = tarfile.open(ova)
            filenames = tar.getnames()
            if len(filenames) == 0:
                raise Exception('Empty OVA')
            for filename in filenames:
                if filename.endswith('.ovf') and not ovf:
                    ovf = tar.getmember(filename)
                    ovf = tar.extractfile(ovf)
                elif filename.endswith('.ovf') and ovf:
                    raise Exception('Multiple OVF files found')
        return ovf

    def parseNetworkSection(self, networkSection):
        if networkSection is not None:
            for network in networkSection.findall('ovf:Network', OVA.namespace):
                return network.get('{%s}name' % OVA.namespace['ovf'])

    def parseVirtualSystem(self, virtualSystem):
        response = []
        if virtualSystem is not None:
            for operatingSystemSection in virtualSystem.findall('ovf:OperatingSystemSection', OVA.namespace):
                operatingSystem = operatingSystemSection.get('{%s}osType' % OVA.namespace['vmw'])
                response.append(OVA.OVFHardwareProperty(type='osType', value=operatingSystem))
            for virtualHardwareSection in virtualSystem.findall('ovf:VirtualHardwareSection', OVA.namespace):
                for item in virtualHardwareSection.findall('ovf:Item', OVA.namespace):
                    resourceSubType = item.find('rasd:ResourceSubType', OVA.namespace)
                    if resourceSubType is not None:
                        #elementName = item.find('rasd:ElementName', OVA.namespace).text.replace(' ', '_')
                        resourceType = item.find('rasd:ResourceType', OVA.namespace).text
                        response.append(OVA.OVFHardwareProperty(type=resourceType,
                                                                value=resourceSubType.text))
            for productSection in virtualSystem.findall('ovf:ProductSection', OVA.namespace):
                category = productSection.find('ovf:Category', OVA.namespace)
                if category is not None:
                    _class = productSection.get('{%s}class' % OVA.namespace['ovf'])
                    instance = productSection.get('{%s}instance' % OVA.namespace['ovf'])
                    for property in productSection.findall('ovf:Property', OVA.namespace):
                        label = property.find('{%s}Label' % OVA.namespace['ovf'])
                        description = property.find('{%s}Description' % OVA.namespace['ovf'])
                        key = property.get('{%s}key' % OVA.namespace['ovf'])
                        try:
                            response.append(OVA.OVFProperty(category=category.text,
                                                    label=label.text,
                                                    description=None if description is None else description.text,
                                                    key=key,
                                                    _class=_class,
                                                    instance=instance))
                        except AttributeError as e:
                            pass

            for vService in virtualSystem.findall('vmw:vServiceDependencySection', OVA.namespace):
                id = vService.get('{%s}id' % OVA.namespace['vmw'])
                response.append(OVA.VServiceDependency(id=id))

        return response

    def cli(self):
        self.network = raw_input('%s: ' % self.networkProperty)
        for property in self.virtualSystemProperties:
            try:
                assert isinstance(property, OVA.OVFProperty)
                prompt = property.label if property.description is None else property.description
                property.value = raw_input('%s: ' % prompt)
            except AssertionError as e:
                pass

    def __str__(self):
        str = ""
        str += '"--net:%s=%s"' % (self.networkProperty, self.network) + " "
        for property in self.virtualSystemProperties:
            if property.value is not None and property.value is not "" and isinstance(property, OVA.OVFProperty):
                str += property.__str__() + " "
            if isinstance(property, OVA.VServiceDependency):
                str += property.__str__() + " "
        return str


    class OVFHardwareProperty(object):
        def __init__(self, **kwargs):
            #NETWORK_DEVICES = ['VirtualE1000', 'VirtualE1000e',
            #                        'VirtualPCNet32', 'VirtualSriovEthernetCard',
            #                        'VirtualVmxnet', 'VirtualVmxnet3']

            #E1000, PCNet32, VmxNet, VmxNet2, VmxNet3
            #lsilogic, buslogic, lsilogicsas, virtualscsi

            self.resourceTypeMap = {'6'}
            self.value = None
            for key, value in kwargs.items():
                setattr(self, key, value)


    class OVFProperty(object):
        def __init__(self, **kwargs):
            self.value = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __str__(self):
            str = '--prop:'
            for i in (self._class, self.key, self.instance):
                if i is not None:
                    if i is not self.instance and self.instance is not None:
                        str += '%s.' % i
                    else:
                        str += i
            str += '="%s"' % self.value
            return str


    class VServiceDependency(object):
        def __init__(self, **kwargs):
            self.value = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __str__(self):
            return '--vService:%s=com.vmware.vim.vsm:extension_vservice' % self.id


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "supply OVA filename"
        sys.exit(1)

    ova = OVA(ova=sys.argv[1])
    ova.cli()

    print ova

